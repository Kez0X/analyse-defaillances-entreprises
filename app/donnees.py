"""
Chargement des données du dashboard.

Règle d'or : l'application ne lit QUE les petits fichiers de `data/dashboard/`
(produits par les notebooks). Jamais SIRENE, les ratios ou le BODACC complets :
ce serait lent et ça saturerait la RAM.

Chaque fichier est lu une seule fois, puis gardé en mémoire (`lru_cache`).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

DASHBOARD = Path(__file__).resolve().parents[1] / "data" / "dashboard"

TOTAL = "Total"  # valeur qui veut dire « toutes les valeurs réunies » dans les cubes

# Ordre d'affichage des tranches (sinon elles sont triées par ordre alphabétique)
ORDRE_AGE = ["< 1 an", "1-3 ans", "3-5 ans", "5-10 ans", "10-20 ans", "20 ans et +", "non renseigné"]
ORDRE_TAILLE = ["< 100 k€", "100-500 k€", "500 k€-2 M€", "2-10 M€", "10 M€ et +", "non renseigné"]
CATEGORIES = ["entrée en défaillance", "aggravation", "issue", "signal précoce", "autre"]

NAF_SECTIONS = {
    "A": "Agriculture", "B": "Industries extractives", "C": "Industrie manufacturière",
    "D": "Énergie", "E": "Eau, déchets", "F": "Construction", "G": "Commerce",
    "H": "Transports", "I": "Hébergement, restauration", "J": "Information, communication",
    "K": "Finance, assurance", "L": "Immobilier", "M": "Activités spécialisées, scientifiques",
    "N": "Services administratifs", "O": "Administration publique", "P": "Enseignement",
    "Q": "Santé, action sociale", "R": "Arts, spectacles", "S": "Autres services",
    "T": "Ménages employeurs", "U": "Extraterritorial",
}
CJ_FAMILLES = {
    "1": "Entrepreneur individuel", "2": "Groupement de droit privé non doté de la personnalité morale",
    "3": "Personne morale de droit étranger", "4": "Personne morale de droit public soumise au droit commercial",
    "5": "Société commerciale", "6": "Autre personne morale immatriculée au RCS",
    "7": "Personne morale de droit administratif", "8": "Organisme privé spécialisé",
    "9": "Groupement de droit privé (associations…)",
}


@lru_cache(maxsize=None)
def lire(nom: str) -> pd.DataFrame:
    """Lit `data/dashboard/<nom>.parquet` (une seule fois)."""
    chemin = DASHBOARD / f"{nom}.parquet"
    if not chemin.exists():
        raise FileNotFoundError(
            f"{chemin} n'existe pas. Lancer d'abord le notebook qui le produit (voir docs/dashboard.md)."
        )
    df = pd.read_parquet(chemin)
    # Les colonnes texte (dimensions) en `category` : 4 à 5 fois moins de RAM
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].astype("category")
    return df


def existe(nom: str) -> bool:
    return (DASHBOARD / f"{nom}.parquet").exists()


def coupe(nom: str, **filtres) -> pd.DataFrame:
    """Sélectionne une « coupe » d'un cube.

    Toute dimension du cube qui n'est pas dans `filtres` est fixée à « Total ».
    Une dimension passée à `None` est laissée libre (on garde toutes ses valeurs, sauf « Total »).

    Exemple : les entrées en défaillance par année, tout le reste réuni
        coupe("cube_principal", categorie="entrée en défaillance", annee=None)
    """
    df = lire(nom)
    dims = [c for c in df.columns if c not in ("categorie", "nb_evenements", "nb_entreprises",
                                                "nb_actives", "entreprises_defaillantes", "taux_pour_mille")]
    masque = pd.Series(True, index=df.index)
    for col in ["categorie", *dims]:
        if col not in df.columns:
            continue
        if col in filtres:
            valeur = filtres[col]
            masque &= (df[col] != TOTAL) if valeur is None else (df[col] == valeur)
        elif col != "categorie":
            masque &= df[col] == TOTAL
    resultat = df[masque].copy()
    # Le résultat est petit : on repasse les dimensions en texte normal (plus simple à manipuler)
    for col in resultat.select_dtypes(include="category").columns:
        resultat[col] = resultat[col].astype(str)
    return resultat


# --------------------------------------------------------------------------- filtres globaux (secteur, région)
TOUS = "tous"

REGIONS = ["Auvergne-Rhône-Alpes", "Bourgogne-Franche-Comté", "Bretagne", "Centre-Val de Loire", "Corse", "Grand Est",
           "Guadeloupe", "Guyane", "Hauts-de-France", "Île-de-France", "La Réunion", "Martinique", "Mayotte",
           "Normandie", "Nouvelle-Aquitaine", "Occitanie", "Pays de la Loire", "Provence-Alpes-Côte d'Azur"]


def libelle_perimetre(secteur, region):
    """« Construction · Bretagne », « Tous secteurs · France entière »…"""
    s = NAF_SECTIONS.get(secteur, "Tous secteurs") if secteur not in (None, TOUS) else "Tous secteurs"
    r = region if region not in (None, TOUS) else "France entière"
    return f"{s} · {r}"


def est_filtre(secteur, region):
    return secteur not in (None, TOUS) or region not in (None, TOUS)


def filtrer(df, secteur, region, col_secteur="naf_section", col_region="region"):
    """Garde les lignes du périmètre choisi (TOUS = pas de filtre)."""
    m = pd.Series(True, index=df.index)
    if secteur not in (None, TOUS):
        m &= df[col_secteur].astype(str) == secteur
    if region not in (None, TOUS):
        m &= df[col_region].astype(str) == region
    return df[m]


def serie_perimetre(secteur, region):
    """Entrées en défaillance par mois dans le périmètre, avec la normale (même mois de 2010-2019),
    l'indice (100 = normal) et le solde cumulé depuis janvier 2020."""
    t = filtrer(lire("evenements_mensuel_perimetre"), secteur, region)
    s = t.groupby("mois")["entrees"].sum()
    mois = pd.Index([f"{a}-{m:02d}" for a in range(2008, 2027) for m in range(1, 13)
                     if f"{a}-{m:02d}" <= "2026-10"], name="mois")
    s = s.reindex(mois, fill_value=0).astype(float)
    ref = s[s.index.str[:4].isin([str(a) for a in range(2010, 2020)])]
    ref = ref.groupby(ref.index.str[5:]).mean()
    d = pd.DataFrame({"entrees": s, "reference": s.index.str[5:].map(ref)}, index=s.index)
    d["indice"] = 100 * d["entrees"] / d["reference"].where(d["reference"] > 0)
    d["ecart"] = d["entrees"] - d["reference"]
    d["solde"] = d["ecart"].where(d.index >= "2020-01").cumsum()
    return d


def bilan_rattrapage(secteur, region):
    """Le fil rouge en chiffres : défaillances « manquantes » pendant le Covid (janvier 2020 - août 2022),
    écart à la normale depuis (positif = rattrapage), et solde aujourd'hui."""
    d = serie_perimetre(secteur, region)
    covid = d.loc["2020-01":"2022-08", "ecart"].sum()
    apres = d.loc["2022-09":, "ecart"].sum()
    return {"manquantes": -covid, "depuis": apres, "solde": covid + apres,
            "part_rattrapee": apres / -covid if covid < 0 else float("nan"),
            "indice_recent": (100 * d.loc["2025-11":, "entrees"].sum() / d.loc["2025-11":, "reference"].sum()
                              if d.loc["2025-11":, "reference"].sum() > 0 else float("nan"))}


def taux_perimetre(secteur, region, annees=("2025",)):
    """Taux de défaillance (‰ des entreprises actives) du périmètre, sur une ou plusieurs années réunies."""
    t = coupe("taux", annee=None, naf_section=secteur if secteur not in (None, TOUS) else TOTAL,
              region=region if region not in (None, TOUS) else TOTAL)
    t = t[t["annee"].astype(str).isin(annees)]
    actives = t["nb_actives"].sum()
    return 1000 * t["entreprises_defaillantes"].sum() / actives if actives else float("nan")


def issues_redressements(secteur, region, annees=range(2008, 2024)):
    """Issue à 36 mois des redressements ouverts (part en %) dans le périmètre, et leur nombre."""
    c = filtrer(lire("parcours_cohortes_perimetre"), secteur, region)
    c = c[c["année d'ouverture"].isin(list(annees))]
    n = c.groupby(c["issue à 36 mois"].astype(str))["entreprises"].sum()
    return 100 * n / n.sum() if n.sum() else n, int(n.sum())


def part_liquidation_directe(secteur, region):
    p = filtrer(lire("parcours_premiere_ouverture"), secteur, region)
    n = p.groupby(p["premiere"].astype(str))["entreprises"].sum()
    return 100 * n.get("Liquidation judiciaire", 0) / n.sum() if n.sum() else float("nan"), int(n.sum())


def delais_perimetre(secteur, region):
    d = lire("parcours_delais_perimetre")
    s = secteur if secteur not in (None, TOUS) else TOTAL
    r = region if region not in (None, TOUS) else TOTAL
    return d[(d["naf_section"].astype(str) == s) & (d["region"].astype(str) == r)]


def risque_profils(secteur, region):
    """% d'exercices suivis d'une faillite dans les 36 mois, par profil financier, dans le périmètre."""
    p = filtrer(lire("profils_risque_perimetre"), secteur, region).groupby("profil")[["exercices", "faillites"]].sum()
    p = p.reindex([1, 2, 3, 4], fill_value=0)
    p["taux"] = 100 * p["faillites"] / p["exercices"]
    return p
