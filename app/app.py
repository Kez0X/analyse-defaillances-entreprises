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
from dash import Dash, Input, Output, callback, dcc, html

import design  # noqa: F401  (enregistre le thème plotly par défaut)
from donnees import NAF_SECTIONS, REGIONS, TOUS, est_filtre, libelle_perimetre

app = Dash(
    __name__,
    use_pages=True,  # chaque fichier de app/pages/ est une page
    # Bootstrap (grille, formulaires) est enregistré dans assets/0_bootstrap.min.css : l'application marche sans
    # Internet. Dash charge les fichiers de assets/ par ordre alphabétique, donc Bootstrap avant design_system.css.
    suppress_callback_exceptions=True,
    title="Défaillances d'entreprises",
)

# Ordre des rubriques dans la barre latérale (chaque page déclare sa rubrique avec `section=`)
RUBRIQUES = ["Exploration", "Analyses", "Bonus", "Outils"]

# Ce que le filtre global change sur chaque page (affiché dans le bandeau)
PORTEE = {
    "/": "le fil rouge et « Et pour vous ? »",
    "/evenements": "les questions 1 et 2",
    "/parcours": "les questions 1 à 3",
    "/secteurs": "la question 2",
    "/signaux": "la question 1",
}


def filtres_globaux():
    """Le périmètre (secteur, région), choisi une fois et appliqué à toutes les pages."""
    secteurs = [{"label": "Tous les secteurs", "value": TOUS}] + [
        {"label": nom, "value": code} for code, nom in NAF_SECTIONS.items() if code not in ("T", "U")]
    regions = [{"label": "France entière", "value": TOUS}] + [{"label": r, "value": r} for r in REGIONS]
    options = dict(clearable=False, searchable=True, persistence=True, persistence_type="session")
    return html.Div([
        html.Div("Votre périmètre", className="ds-nav__section"),
        html.Div([
            html.Label("Secteur", className="ds-perimetre__label"),
            dcc.Dropdown(secteurs, TOUS, id="filtre-secteur", **options),
            html.Label("Région", className="ds-perimetre__label"),
            dcc.Dropdown(regions, TOUS, id="filtre-region", **options),
        ], className="ds-perimetre"),
    ])


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
        filtres_globaux(),
        *blocs,
        html.Div([
            "Projet M2 Analyse de données", html.Br(), "Luka & Lucas", html.Br(),
            "Sources : BODACC, SIRENE (Insee), ratios BCE / INPI",
        ], className="ds-sidebar__footer"),
    ], className="ds-sidebar")


app.layout = html.Div([
    dcc.Location(id="url"),
    barre_laterale(),
    html.Main([html.Div(id="bandeau-perimetre"), dash.page_container], className="ds-main"),
], className="ds-shell")


@callback(Output("bandeau-perimetre", "children"), Input("filtre-secteur", "value"), Input("filtre-region", "value"),
          Input("url", "pathname"))
def bandeau(secteur, region, chemin):
    """Rappelle le périmètre choisi, et ce qu'il change sur la page affichée."""
    if not est_filtre(secteur, region):
        return None
    portee = PORTEE.get(chemin)
    detail = (f"Sur cette page, il s'applique à {portee} ; le reste est national." if portee
              else "Cette page n'en dépend pas : tout y est national.")
    return html.Div([html.Span("Périmètre", className="ds-bandeau__label"),
                     html.B(libelle_perimetre(secteur, region)), html.Span(detail, className="ds-bandeau__detail")],
                    className="ds-bandeau")

if __name__ == "__main__":
    app.run(debug=True)
