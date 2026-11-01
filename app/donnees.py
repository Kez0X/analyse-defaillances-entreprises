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
