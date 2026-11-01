"""Réseaux (axes 7 à 9) — page de Luka."""
import dash

from design import en_construction

dash.register_page(__name__, path="/reseaux", name="Réseaux", order=3, section="Analyses")


def layout():
    return en_construction(
        "Réseaux", "Analyses · axes 7 à 9",
        ["Le graphe des entreprises liées (annonces collectives, extensions de procédure).",
         "Le graphe des secteurs qui « souffrent ensemble » (courbes de défaillance similaires).",
         "Le graphe des départements, avec une carte des communautés."],
        ["Similarité cosinus → graphe → node2vec",
         "Centralités, communautés de Louvain, small world"],
        "Luka",
    )
