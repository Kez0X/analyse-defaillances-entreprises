"""
Chargement économe en RAM des données SIRENE et ratios BCE/INPI.

Pourquoi : charger `sirene_ul.parquet` tel quel en pandas coûte ~9 Go de RAM
(30 M lignes x 21 colonnes texte). Avec les sièges et les ratios, la machine
(15 Go) sature et le kernel meurt.

Ce module :
  - lit les parquets par row group (pic mémoire borné) ;
  - ne charge que les colonnes demandées ;
  - encode les colonnes texte en `category` et le SIREN en int64 ;
  - convertit une fois pour toutes le CSV des ratios en parquet typé (float32) ;
  - fournit `free_memory()` pour rendre la RAM au système entre deux étapes.

Usage dans un notebook :
    import sys; sys.path.append("../scripts")
    from data_utils import load_sirene_ul, load_sirene_sieges, load_ratios, free_memory, mem
"""
from __future__ import annotations

import ctypes
import gc
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as pv
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"

SIRENE_UL = PROCESSED / "sirene_ul.parquet"
SIRENE_SIEGES = PROCESSED / "sirene_sieges.parquet"
RATIOS_CSV = RAW / "ratios" / "ratios_inpi_bce.csv.gz"
RATIOS_PARQUET = PROCESSED / "ratios.parquet"
SIRENE_ETAB_ZIP = RAW / "sirene" / "StockEtablissement_utf8.zip"
SIRENE_ETAB = PROCESSED / "sirene_etablissements.parquet"
ETAB_COLS = [
    "siren",
    "etablissementSiege",
    "etatAdministratifEtablissement",
    "trancheEffectifsEtablissement",
    "anneeEffectifsEtablissement",
    "dateCreationEtablissement",
]

# Colonnes gardées par défaut (les plus utiles pour la défaillance)
UL_DEFAULT_COLS = [
    "siren",
    "dateCreationUniteLegale",
    "trancheEffectifsUniteLegale",
    "categorieEntreprise",
    "etatAdministratifUniteLegale",
    "categorieJuridiqueUniteLegale",
    "activitePrincipaleUniteLegale",
    "caractereEmployeurUniteLegale",
]
SIEGES_DEFAULT_COLS = [
    "siren",
    "codeCommuneEtablissement",
    "codePostalEtablissement",
    "etatAdministratifEtablissement",
]
RATIOS_TEXT_COLS = {"siren", "date_cloture_exercice", "type_bilan", "confidentiality"}


# --------------------------------------------------------------------------- RAM
def mem() -> str:
    """RAM utilisée par le process et RAM encore disponible sur la machine."""
    import psutil

    rss = psutil.Process().memory_info().rss / 1e9
    avail = psutil.virtual_memory().available / 1e9
    return f"process : {rss:.2f} Go | disponible : {avail:.2f} Go"


def free_memory() -> str:
    """Force le GC Python, vide le pool Arrow et rend la RAM libre à l'OS."""
    gc.collect()
    pa.default_memory_pool().release_unused()
    try:  # glibc : sans ça, la RAM libérée reste réservée par le process
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except OSError:
        pass
    return mem()


def check_ram(min_free_gb: float = 2.0) -> None:
    """Lève une erreur claire au lieu de laisser le kernel se faire tuer."""
    import psutil

    avail = psutil.virtual_memory().available / 1e9
    if avail < min_free_gb:
        raise MemoryError(
            f"Seulement {avail:.1f} Go de RAM libre (< {min_free_gb} Go). "
            "Supprimer des objets (`del df`) puis appeler free_memory()."
        )


# --------------------------------------------------------------------------- lecture
def _read_parquet_light(
    path: Path,
    columns: list[str] | None,
    filters=None,
) -> pd.DataFrame:
    """Lit un parquet row group par row group, texte -> dictionnaire, siren -> int64."""
    pf = pq.ParquetFile(path)
    columns = columns or pf.schema_arrow.names
    text_cols = [
        c for c in columns
        if c != "siren" and pa.types.is_string(pf.schema_arrow.field(c).type)
    ]

    pieces = []
    for i in range(pf.num_row_groups):
        check_ram()
        t = pf.read_row_group(i, columns=columns)
        if filters is not None:
            t = t.filter(filters)
        if "siren" in columns:
            t = t.set_column(
                t.schema.get_field_index("siren"), "siren", pc.cast(t["siren"], pa.int64())
            )
        for c in text_cols:
            t = t.set_column(t.schema.get_field_index(c), c, pc.dictionary_encode(t[c]))
        pieces.append(t)

    table = pa.concat_tables(pieces).unify_dictionaries()
    del pieces
    df = table.to_pandas(self_destruct=True)  # libère l'Arrow au fur et à mesure
    del table
    free_memory()
    return df


def load_sirene_ul(columns: list[str] | None = UL_DEFAULT_COLS, filters=None) -> pd.DataFrame:
    """Unités légales SIRENE. `columns=None` pour tout charger.

    `filters` : expression pyarrow appliquée avant conversion, ex.
        import pyarrow.compute as pc
        load_sirene_ul(filters=pc.field("etatAdministratifUniteLegale") == "A")
    """
    return _read_parquet_light(SIRENE_UL, columns, filters)


def load_sirene_sieges(columns: list[str] | None = SIEGES_DEFAULT_COLS, filters=None) -> pd.DataFrame:
    """Établissements sièges SIRENE. `columns=None` pour tout charger."""
    return _read_parquet_light(SIRENE_SIEGES, columns, filters)


def build_etablissements_parquet(force: bool = False) -> Path:
    """Convertit le StockEtablissement (CSV de 10 Go dans le zip) en parquet léger.

    Lecture en streaming directement dans le zip, sans décompresser sur le disque.
    On ne garde que ETAB_COLS (tout en texte, comme les autres parquets SIRENE).
    """
    import zipfile

    if SIRENE_ETAB.exists() and not force:
        return SIRENE_ETAB
    with zipfile.ZipFile(SIRENE_ETAB_ZIP) as z, z.open(z.namelist()[0]) as f:
        reader = pv.open_csv(
            f,
            read_options=pv.ReadOptions(block_size=64 << 20),
            convert_options=pv.ConvertOptions(
                include_columns=ETAB_COLS,
                column_types={c: pa.string() for c in ETAB_COLS},
                strings_can_be_null=False,
            ),
        )
        writer = None
        for batch in reader:
            t = pa.Table.from_batches([batch])
            if writer is None:
                writer = pq.ParquetWriter(SIRENE_ETAB, t.schema, compression="zstd")
            writer.write_table(t)
        if writer is not None:
            writer.close()
    free_memory()
    return SIRENE_ETAB


def load_sirene_etablissements(columns: list[str] | None = None, filters=None) -> pd.DataFrame:
    """Tous les établissements SIRENE (crée le parquet au premier appel, ~40 M lignes)."""
    build_etablissements_parquet()
    return _read_parquet_light(SIRENE_ETAB, columns, filters)


# --------------------------------------------------------------------------- ratios
def build_ratios_parquet(force: bool = False) -> Path:
    """Convertit le CSV.gz des ratios en parquet typé, en streaming (une seule fois)."""
    if RATIOS_PARQUET.exists() and not force:
        return RATIOS_PARQUET

    header = pv.open_csv(
        RATIOS_CSV, parse_options=pv.ParseOptions(delimiter=";")
    ).schema.names
    col_types = {
        c: (pa.string() if c in RATIOS_TEXT_COLS else pa.float32()) for c in header
    }
    reader = pv.open_csv(
        RATIOS_CSV,
        read_options=pv.ReadOptions(block_size=64 << 20),
        parse_options=pv.ParseOptions(delimiter=";"),
        convert_options=pv.ConvertOptions(column_types=col_types),
    )
    writer = None
    for batch in reader:
        t = pa.Table.from_batches([batch])
        t = t.set_column(0, "siren", pc.cast(t["siren"], pa.int64()))
        if writer is None:
            writer = pq.ParquetWriter(RATIOS_PARQUET, t.schema, compression="zstd")
        writer.write_table(t)
    if writer is not None:
        writer.close()
    free_memory()
    return RATIOS_PARQUET


def load_ratios(columns: list[str] | None = None, filters=None) -> pd.DataFrame:
    """Ratios financiers BCE/INPI (crée le parquet au premier appel)."""
    build_ratios_parquet()
    df = _read_parquet_light(RATIOS_PARQUET, columns, filters)
    if "date_cloture_exercice" in df.columns:
        df["date_cloture_exercice"] = pd.to_datetime(
            df["date_cloture_exercice"].astype("string"), errors="coerce"
        )
    return df


# --------------------------------------------------------------------------- NAF
NAF_SECTIONS = {
    "A": (1, 3), "B": (5, 9), "C": (10, 33), "D": (35, 35), "E": (36, 39), "F": (41, 43),
    "G": (45, 47), "H": (49, 53), "I": (55, 56), "J": (58, 63), "K": (64, 66), "L": (68, 68),
    "M": (69, 75), "N": (77, 82), "O": (84, 84), "P": (85, 85), "Q": (86, 88), "R": (90, 93),
    "S": (94, 96), "T": (97, 98), "U": (99, 99),
}
NAF_SECTION_NOMS = {
    "A": "Agriculture", "B": "Industries extractives", "C": "Industrie manufacturière",
    "D": "Énergie", "E": "Eau, déchets", "F": "Construction", "G": "Commerce",
    "H": "Transports", "I": "Hébergement, restauration", "J": "Information, communication",
    "K": "Finance, assurance", "L": "Immobilier", "M": "Activités spécialisées, scientifiques",
    "N": "Services administratifs", "O": "Administration publique", "P": "Enseignement",
    "Q": "Santé, action sociale", "R": "Arts, spectacles", "S": "Autres services",
    "T": "Ménages employeurs", "U": "Extraterritorial",
}


def naf_section(code_naf: pd.Series) -> pd.Series:
    """Section NAFRev2 (lettre A-U) à partir d'un code NAF type '47.11F'."""
    div = pd.to_numeric(code_naf.astype("string").str[:2], errors="coerce")
    out = pd.Series(pd.NA, index=code_naf.index, dtype="string")
    for lettre, (a, b) in NAF_SECTIONS.items():
        out[div.between(a, b)] = lettre
    return out.astype("category")


NAF_DIVISIONS = {
    "01": "Culture, production animale, chasse", "02": "Sylviculture, exploitation forestière",
    "03": "Pêche et aquaculture", "05": "Extraction de houille et de lignite",
    "06": "Extraction d'hydrocarbures", "07": "Extraction de minerais métalliques",
    "08": "Autres industries extractives", "09": "Services de soutien aux industries extractives",
    "10": "Industries alimentaires", "11": "Fabrication de boissons", "12": "Fabrication de produits à base de tabac",
    "13": "Fabrication de textiles", "14": "Industrie de l'habillement", "15": "Industrie du cuir et de la chaussure",
    "16": "Travail du bois", "17": "Industrie du papier et du carton", "18": "Imprimerie et reproduction",
    "19": "Cokéfaction et raffinage", "20": "Industrie chimique", "21": "Industrie pharmaceutique",
    "22": "Produits en caoutchouc et en plastique", "23": "Autres produits minéraux non métalliques",
    "24": "Métallurgie", "25": "Fabrication de produits métalliques",
    "26": "Produits informatiques, électroniques et optiques", "27": "Fabrication d'équipements électriques",
    "28": "Fabrication de machines et équipements", "29": "Industrie automobile",
    "30": "Autres matériels de transport", "31": "Fabrication de meubles", "32": "Autres industries manufacturières",
    "33": "Réparation et installation de machines", "35": "Électricité, gaz, vapeur et air conditionné",
    "36": "Captage, traitement et distribution d'eau", "37": "Collecte et traitement des eaux usées",
    "38": "Collecte et traitement des déchets, récupération", "39": "Dépollution et gestion des déchets",
    "41": "Construction de bâtiments", "42": "Génie civil", "43": "Travaux de construction spécialisés",
    "45": "Commerce et réparation automobile", "46": "Commerce de gros", "47": "Commerce de détail",
    "49": "Transports terrestres", "50": "Transports par eau", "51": "Transports aériens",
    "52": "Entreposage et services auxiliaires des transports", "53": "Poste et courrier",
    "55": "Hébergement", "56": "Restauration", "58": "Édition",
    "59": "Cinéma, vidéo, télévision, musique enregistrée", "60": "Programmation et diffusion",
    "61": "Télécommunications", "62": "Programmation, conseil informatique", "63": "Services d'information",
    "64": "Services financiers", "65": "Assurance", "66": "Auxiliaires de services financiers et d'assurance",
    "68": "Activités immobilières", "69": "Activités juridiques et comptables",
    "70": "Sièges sociaux, conseil de gestion", "71": "Architecture, ingénierie, contrôle technique",
    "72": "Recherche-développement", "73": "Publicité et études de marché",
    "74": "Autres activités spécialisées, scientifiques et techniques", "75": "Activités vétérinaires",
    "77": "Location et location-bail", "78": "Activités liées à l'emploi", "79": "Agences de voyage, voyagistes",
    "80": "Enquêtes et sécurité", "81": "Services aux bâtiments, aménagement paysager",
    "82": "Soutien administratif aux entreprises", "84": "Administration publique",
    "85": "Enseignement", "86": "Santé humaine", "87": "Hébergement médico-social et social",
    "88": "Action sociale sans hébergement", "90": "Activités créatives, artistiques et de spectacle",
    "91": "Bibliothèques, archives, musées", "92": "Jeux de hasard et d'argent",
    "93": "Activités sportives, récréatives et de loisirs", "94": "Organisations associatives",
    "95": "Réparation d'ordinateurs et de biens personnels", "96": "Autres services personnels",
    "97": "Ménages employeurs de personnel domestique", "98": "Activités des ménages pour usage propre",
    "99": "Organisations extraterritoriales",
}
