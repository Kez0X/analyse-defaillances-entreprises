"""Profils financiers (axes 10 et 11) — page de Luka."""
import dash

from design import en_construction

dash.register_page(__name__, path="/profils", name="Profils financiers", order=4, section="Analyses")


def layout():
    return en_construction(
        "Profils financiers", "Analyses · axes 10 et 11",
        ["Les grands profils financiers des entreprises, et le taux de faillite de chaque profil.",
         "La typologie des secteurs et des départements."],
        ["ACP, t-SNE", "k-means, mélange gaussien, DBSCAN, silhouette"],
        "Luka",
    )
