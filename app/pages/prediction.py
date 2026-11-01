"""Bonus : prédire la faillite (axe 12) — page de Luka."""
import dash

from design import en_construction

dash.register_page(__name__, path="/prediction", name="Prédiction", order=5, section="Bonus")


def layout():
    return en_construction(
        "Prédire la faillite", "Bonus · axe 12",
        ["Prédire la faillite dans les 36 mois à partir des ratios et du profil de l'entreprise.",
         "Les variables qui comptent le plus."],
        ["Classification supervisée"],
        "Luka",
    )
