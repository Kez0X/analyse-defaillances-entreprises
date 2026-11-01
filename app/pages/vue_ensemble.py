"""Vue d'ensemble (axes 1 à 5) — page de Lucas.

Cette page contient un premier exemple qui marche (évolution par année),
à compléter : territoire, secteur, forme juridique, âge, taille.
Toutes les données viennent des cubes de `data/dashboard/` (voir docs/dashboard.md).
Les composants et couleurs viennent de design.py (voir la page « Design system »).
"""
import dash
import plotly.express as px
from dash import Input, Output, callback, dcc, html

from design import (COULEURS_CATEGORIES, badge, boutons_segmentes, carte, couleurs_annees, encadre, entete,
                    filtre, filtres, graphe, zone_covid)
from donnees import CATEGORIES, coupe

dash.register_page(__name__, path="/vue-ensemble", name="Vue d'ensemble", order=1, section="Exploration")


def layout():
    return html.Div([
        entete(
            "Vue d'ensemble",
            "Comment évoluent les défaillances dans le temps, et où, dans quels secteurs, "
            "pour quels profils d'entreprises ?",
            surtitre="Exploration · axes 1 à 5",
            badges=[badge("Responsable : Lucas")],
        ),
        filtres(
            filtre("Type d'événement",
                   dcc.Dropdown(CATEGORIES, "entrée en défaillance", id="ve-categorie", clearable=False)),
            filtre("Compter",
                   boutons_segmentes("ve-mesure",
                                     [{"label": "Entreprises", "value": "nb_entreprises"},
                                      {"label": "Événements", "value": "nb_evenements"}],
                                     "nb_entreprises")),
        ),
        carte(
            graphe("ve-annees", hauteur=380),
            titre="Évolution par année",
            description="Une entreprise peut avoir plusieurs événements : « Entreprises » compte chaque SIREN une fois.",
            pied="En pâle : années incomplètes, 2007 (fin d'année) et 2026 (jusqu'à fin octobre). Source : cube OLAP.",
            className="mb-4",
        ),
        encadre("territoires, secteurs, forme juridique, âge, taille et taux de défaillance.",
                titre="À compléter par Lucas :"),
    ])


@callback(Output("ve-annees", "figure"), Input("ve-categorie", "value"), Input("ve-mesure", "value"))
def graphe_annees(categorie, mesure):
    df = coupe("cube_principal", categorie=categorie, annee=None)
    df = df.assign(annee=df["annee"].astype(int)).sort_values("annee")
    libelle = "Entreprises" if mesure == "nb_entreprises" else "Événements"
    fig = px.bar(df, x="annee", y=mesure, labels={"annee": "", mesure: libelle})
    fig.update_traces(marker_color=couleurs_annees(df["annee"], COULEURS_CATEGORIES[categorie]),
                      hovertemplate="%{x} : %{y:,.0f}<extra></extra>")
    fig.update_layout(margin=dict(t=16), xaxis=dict(dtick=2))
    return zone_covid(fig)
