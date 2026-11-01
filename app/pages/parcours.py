"""Parcours des procédures (axe 6) — page de Luka."""
import dash

from design import en_construction

dash.register_page(__name__, path="/parcours", name="Parcours des procédures", order=2, section="Analyses")


def layout():
    return en_construction(
        "Le parcours des procédures", "Analyses · axe 6",
        ["Le graphe des étapes (sauvegarde, redressement, liquidation, plan, cession, clôture), "
         "pondéré par le nombre d'entreprises qui passent d'une étape à l'autre.",
         "Les chemins qui mènent le plus souvent à la liquidation, avant et après le Covid."],
        ["Graphe orienté pondéré (networkx)", "Centralités, PageRank"],
        "Luka",
    )
