"""
Dashboard : les défaillances d'entreprises en France (2008-2026).

Lancer depuis la racine du projet :
    .venv/bin/python app/app.py
puis ouvrir http://127.0.0.1:8050

Le style vient de assets/design_system.css (chargé automatiquement par Dash)
et de design.py (thème des graphiques + composants).
"""
import dash
import dash_bootstrap_components as dbc
from dash import Dash, html

import design  # noqa: F401  (enregistre le thème plotly par défaut)

app = Dash(
    __name__,
    use_pages=True,  # chaque fichier de app/pages/ est une page
    external_stylesheets=[dbc.themes.BOOTSTRAP],  # grille et formulaires ; le style vient de assets/
    suppress_callback_exceptions=True,
    title="Défaillances d'entreprises",
)

# Ordre des rubriques dans la barre latérale (chaque page déclare sa rubrique avec `section=`)
RUBRIQUES = ["Exploration", "Analyses", "Bonus", "Outils"]


def barre_laterale():
    blocs = []
    for rubrique in RUBRIQUES:
        pages = [p for p in dash.page_registry.values() if p.get("section") == rubrique]
        if not pages:
            continue
        blocs.append(html.Div([
            html.Div(rubrique, className="ds-nav__section"),
            dbc.Nav([
                dbc.NavLink([html.Span(className="ds-nav__dot"), p["name"]],
                            href=p["relative_path"], active="exact")
                for p in pages
            ], vertical=True, pills=True, className="ds-nav"),
        ]))
    return html.Aside([
        html.Div([
            html.Div(className="ds-brand__mark"),
            html.Div("Défaillances d'entreprises", className="ds-brand__title"),
            html.Div("France, 2008 – octobre 2026", className="ds-brand__subtitle"),
        ], className="ds-brand"),
        *blocs,
        html.Div([
            "Projet M2 Analyse de données", html.Br(), "Luka & Lucas", html.Br(),
            "Sources : BODACC, SIRENE (Insee), ratios BCE / INPI",
        ], className="ds-sidebar__footer"),
    ], className="ds-sidebar")


app.layout = html.Div([
    barre_laterale(),
    html.Main(dash.page_container, className="ds-main"),
], className="ds-shell")

if __name__ == "__main__":
    app.run(debug=True)
