"""Télécharge les données brutes du projet.

Sources :
  - BODACC (DILA) : annonces de procédures collectives (sauvegarde, redressement,
    liquidation, plans, clôtures...), via l'API OpenDataSoft de la DILA.
  - SIRENE (Insee) : stock des unités légales (toutes les entreprises de France),
    et en option le stock des établissements (localisation, très volumineux).
  - Ratios financiers BCE / INPI : indicateurs issus des comptes annuels déposés,
    via l'API data.economie.gouv.fr.

Usage :
  python scripts/download_data.py                        # tout (sauf établissements SIRENE)
  python scripts/download_data.py --only bodacc --years 2015-2025
  python scripts/download_data.py --with-etablissements  # + StockEtablissement (~3 Go)
  python scripts/download_data.py --force                # re-télécharge même si présent
"""

import argparse
import csv
import gzip
import io
import re
import sys
from datetime import date
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
DOCS_DIR = ROOT / "docs"

BODACC_URL = (
    "https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/"
    "catalog/datasets/annonces-commerciales/exports/csv"
)
BODACC_FIELDS = [
    "id", "dateparution", "typeavis_lib", "numerodepartement", "region_code",
    "tribunal", "commercant", "ville", "cp", "registre", "listepersonnes",
    "jugement", "parutionavisprecedent",
]
BODACC_FIRST_YEAR = 2008  # premières annonces disponibles en open data

SIRENE_API_URL = (
    "https://www.data.gouv.fr/api/1/datasets/"
    "base-sirene-des-entreprises-et-de-leurs-etablissements-siren-siret/"
)
# Titres des ressources data.gouv à récupérer (format CSV zippé, pas parquet)
SIRENE_UL_RE = re.compile(r"^Sirene : Fichier StockUniteLegale - ", re.IGNORECASE)
SIRENE_ETAB_RE = re.compile(r"^Sirene : Fichier StockEtablissement - ", re.IGNORECASE)
SIRENE_DOC_RE = re.compile(r"(stockunitelegale|stocketablissement)-311", re.IGNORECASE)

RATIOS_URL = (
    "https://data.economie.gouv.fr/api/explore/v2.1/"
    "catalog/datasets/ratios_inpi_bce/exports/csv"
)


def rel(path: Path) -> Path:
    return path.relative_to(ROOT)


def download(url: str, dest: Path, force: bool = False, params: dict | None = None) -> None:
    """Télécharge url vers dest ; compresse à la volée si dest se termine par .gz."""
    if dest.exists() and not force:
        print(f"  [déjà présent] {rel(dest)}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    opener = gzip.open if dest.suffix == ".gz" else open
    print(f"  [téléchargement] {rel(dest)} ...", flush=True)
    with requests.get(url, params=params, stream=True, timeout=(30, 900)) as r:
        r.raise_for_status()
        with opener(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    tmp.rename(dest)
    print(f"  [ok] {rel(dest)} ({dest.stat().st_size / 1e6:.0f} Mo)")


# --------------------------------------------------------------------------- BODACC

def parse_years(spec: str | None) -> list[int]:
    if spec is None:
        return list(range(BODACC_FIRST_YEAR, date.today().year + 1))
    years = set()
    for part in spec.split(","):
        if "-" in part:
            start, end = part.split("-")
            years.update(range(int(start), int(end) + 1))
        else:
            years.add(int(part))
    return sorted(years)


def fetch_bodacc_month(year: int, month: int) -> list[list[str]]:
    start = date(year, month, 1)
    end = date(year + month // 12, month % 12 + 1, 1)
    params = {
        "select": ",".join(BODACC_FIELDS),
        "where": (
            f'familleavis="collective" and dateparution>=date\'{start}\' '
            f"and dateparution<date'{end}'"
        ),
        "delimiter": ";",
    }
    r = requests.get(BODACC_URL, params=params, timeout=(30, 600))
    r.raise_for_status()
    rows = list(csv.reader(io.StringIO(r.content.decode("utf-8-sig")), delimiter=";"))
    return rows[1:]  # sans l'en-tête


def download_bodacc(years: list[int], force: bool) -> None:
    print("== BODACC : procédures collectives ==")
    today = date.today()
    out_dir = RAW_DIR / "bodacc"
    out_dir.mkdir(parents=True, exist_ok=True)
    for year in years:
        dest = out_dir / f"procedures_collectives_{year}.csv.gz"
        # L'année en cours est toujours incomplète : on la re-télécharge à chaque fois
        if dest.exists() and not force and year != today.year:
            print(f"  [déjà présent] {rel(dest)}")
            continue
        last_month = today.month if year == today.year else 12
        tmp = dest.with_suffix(dest.suffix + ".part")
        n = 0
        with gzip.open(tmp, "wt", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(BODACC_FIELDS)
            for month in range(1, last_month + 1):
                rows = fetch_bodacc_month(year, month)
                writer.writerows(rows)
                n += len(rows)
        tmp.rename(dest)
        print(f"  [ok] {rel(dest)} ({n:,} annonces)")


# --------------------------------------------------------------------------- SIRENE

def download_sirene(with_etablissements: bool, force: bool) -> None:
    print("== SIRENE (Insee) ==")
    resources = requests.get(SIRENE_API_URL, timeout=60).json()["resources"]
    out_dir = RAW_DIR / "sirene"
    for res in resources:
        title, url = res["title"], res["url"]
        filename = url.rsplit("/", 1)[-1]
        if res["format"] == "zip" and SIRENE_UL_RE.match(title):
            download(url, out_dir / "StockUniteLegale_utf8.zip", force)
        elif res["format"] == "zip" and SIRENE_ETAB_RE.match(title) and with_etablissements:
            download(url, out_dir / "StockEtablissement_utf8.zip", force)
        elif SIRENE_DOC_RE.search(filename) and "historique" not in filename.lower():
            download(url, DOCS_DIR / "sirene" / filename, force)


# --------------------------------------------------------------------------- Ratios

def download_ratios(force: bool) -> None:
    print("== Ratios financiers BCE / INPI ==")
    print("  (export complet ~7 M de lignes : ~2 min avant le début du transfert, puis ~20 min)")
    download(RATIOS_URL, RAW_DIR / "ratios" / "ratios_inpi_bce.csv.gz", force, params={"delimiter": ";"})


# --------------------------------------------------------------------------- main

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", choices=["bodacc", "sirene", "ratios"], action="append",
                        help="Ne télécharger que cette source (répétable)")
    parser.add_argument("--years", help="Années BODACC, ex. '2015-2025' ou '2019,2023-2025'")
    parser.add_argument("--with-etablissements", action="store_true",
                        help="Télécharger aussi le StockEtablissement SIRENE (~3 Go)")
    parser.add_argument("--force", action="store_true", help="Re-télécharger les fichiers existants")
    args = parser.parse_args()

    sources = set(args.only or ["bodacc", "sirene", "ratios"])
    if "bodacc" in sources:
        download_bodacc(parse_years(args.years), args.force)
    if "sirene" in sources:
        download_sirene(args.with_etablissements, args.force)
    if "ratios" in sources:
        download_ratios(args.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
