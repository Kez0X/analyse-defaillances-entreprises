"""Design system : la référence visuelle du dashboard (couleurs, composants, règles)."""
import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import dcc, html

from design import (AUTRE, COULEURS_CATEGORIES, ENCRE, SEQUENTIELLE, SERIES, STATUT, SURFACE, badge,
                    boutons_segmentes, carte, chiffre_cle, encadre, entete, filtre, filtres, graphe)

# Pas de `section` : la page n'apparaît pas dans la barre latérale, mais reste accessible à l'adresse /design-system
dash.register_page(__name__, path="/design-system", name="Design system", order=9)


def nuancier(couleurs, colonnes=4):
    """Une grille de pastilles : [(nom, hex, rôle), ...]."""
    return dbc.Row([
        dbc.Col(html.Div([
            html.Div(className="ds-swatch__color", style={"background": hexa}),
            html.Div([html.B(nom), html.Br(), hexa, html.Br(), role], className="ds-swatch__meta"),
        ], className="ds-swatch"), xs=6, md=12 // colonnes, className="mb-3")
        for nom, hexa, role in couleurs
    ])


def exemple_categories():
    """Les catégories d'événements, chacune dans sa couleur attitrée."""
    noms = list(COULEURS_CATEGORIES)
    valeurs = [1016, 295, 1116, 24, 889]
    fig = go.Figure(go.Bar(
        x=valeurs, y=noms, orientation="h",
        marker_color=[COULEURS_CATEGORIES[n] for n in noms],
        hovertemplate="%{y} : %{x} milliers<extra></extra>",
        text=[f"{v} k" for v in valeurs], textposition="outside", textfont=dict(color=ENCRE["secondaire"]),
    ))
    fig.update_traces(cliponaxis=False)
    fig.update_layout(margin=dict(t=8, r=48), yaxis=dict(autorange="reversed"),
                      xaxis=dict(showgrid=True, range=[0, max(valeurs) * 1.15]), showlegend=False)
    return fig


def layout():
    return html.Div([
        entete(
            "Design system",
            "Les couleurs, les composants et les règles du dashboard. Tout est défini à deux endroits : "
            "app/assets/design_system.css (les variables CSS) et app/design.py (le thème des graphiques et les "
            "composants Python). Pour un nouveau graphique, on réutilise ces briques au lieu de choisir des couleurs à la main.",
            surtitre="Référence interne",
            badges=[badge("assets/design_system.css"), badge("design.py")],
        ),

        html.H2("Couleurs", className="ds-card__title mb-3", style={"fontSize": "18px"}),
        dbc.Row([
            dbc.Col(carte(nuancier([
                ("Page", SURFACE["page"], "fond de la page"),
                ("Carte", SURFACE["carte"], "cartes, graphiques"),
                ("Retrait", SURFACE["retrait"], "zones en creux"),
                ("Barre latérale", "#161615", "navigation"),
            ]), titre="Surfaces"), lg=6, className="mb-4"),
            dbc.Col(carte(nuancier([
                ("Encre principale", ENCRE["primaire"], "titres, valeurs"),
                ("Encre secondaire", ENCRE["secondaire"], "textes, légendes"),
                ("Encre discrète", ENCRE["discrete"], "axes, notes"),
                ("Accent", "#2a78d6", "liens, sélection"),
            ]), titre="Encre et accent"), lg=6, className="mb-4"),
        ]),
        carte(
            nuancier([(f"Série {i + 1}", c, r) for i, (c, r) in enumerate(zip(
                SERIES[:5], ["entrée en défaillance", "aggravation", "issue", "signal précoce", "—"]))]
                + [("Autre", AUTRE, "autre, non renseigné")], colonnes=6),
            titre="Séries des graphiques (ordre fixe)",
            description="Les couleurs sont prises dans cet ordre, jamais au hasard. Cet ordre a été vérifié pour "
                        "que deux couleurs voisines restent distinctes, y compris pour les personnes daltoniennes.",
            pied="Le jaune, le vert d'eau et le rose sont un peu pâles sur fond clair : un graphique qui les "
                 "utilise doit toujours avoir une légende et des infobulles.",
            className="mb-4",
        ),
        dbc.Row([
            dbc.Col(carte(
                html.Div(style={"height": "40px", "borderRadius": "8px",
                                "background": f"linear-gradient(90deg, {', '.join(SEQUENTIELLE)})"}),
                html.Div([html.Span("faible"), html.Span("élevé", style={"float": "right"})],
                         className="ds-stat__detail mt-2"),
                titre="Échelle séquentielle",
                description="Une seule teinte, du clair au foncé : pour une quantité (cartes, matrices).",
            ), lg=6, className="mb-4"),
            dbc.Col(carte(
                nuancier([(n.capitalize(), c, "statut") for n, c in STATUT.items()]),
                titre="Statut (réservé)",
                description="Uniquement pour un état (bon, attention, grave, critique), toujours avec un libellé. "
                            "Jamais pour une série de données.",
            ), lg=6, className="mb-4"),
        ]),

        html.H2("Composants", className="ds-card__title mb-3 mt-2", style={"fontSize": "18px"}),
        dbc.Row([
            dbc.Col(chiffre_cle("chiffre_cle()", "60 911", "un libellé, une valeur, un détail"), md=4, className="mb-4"),
            dbc.Col(chiffre_cle("Avec une évolution", "+34 %", "vs 2019",
                                evolution=("plus de défaillances", "up")), md=4, className="mb-4"),
            dbc.Col(carte(
                html.Div([badge("badge()"), " ", badge("accent", "accent"), " ", badge("warning", "warning"), " ",
                          badge("avec un point", couleur=SERIES[0])]),
                titre="Badges",
            ), md=4, className="mb-4"),
        ]),
        filtres(
            filtre("filtre() + Dropdown", dcc.Dropdown(["option A", "option B"], "option A", clearable=False,
                                                       id="ds-demo-dropdown")),
            filtre("boutons_segmentes()", boutons_segmentes("ds-demo-seg", [{"label": "Entreprises", "value": 1},
                                                                            {"label": "Événements", "value": 2}], 1)),
        ),
        dbc.Row([
            dbc.Col(carte(
                graphe("ds-demo-graphe", exemple_categories(), hauteur=260),
                titre="carte() + graphe()",
                description="Chaque catégorie d'événement garde sa couleur partout (COULEURS_CATEGORIES).",
                pied="Exemple fictif (en milliers).",
            ), lg=7, className="mb-4"),
            dbc.Col(html.Div([
                encadre("une note d'information pour aider à lire un graphique.", titre="encadre()"),
                html.Div(className="mb-3"),
                encadre("une mise en garde (données incomplètes, rupture Covid…).", titre="encadre(variante='warning')",
                        variante="warning"),
            ]), lg=5, className="mb-4"),
        ]),

        html.H2("Règles des graphiques", className="ds-card__title mb-3 mt-2", style={"fontSize": "18px"}),
        carte(html.Ul([
            html.Li("Le thème plotly « defaillances » est appliqué automatiquement : ne pas changer les polices, "
                    "fonds ou grilles à la main."),
            html.Li("Les couleurs suivent l'ordre fixe des séries, et restent attachées à la même chose même quand on filtre."),
            html.Li("Avec 2 séries ou plus : toujours une légende. Avec une seule série : pas de légende, le titre suffit."),
            html.Li("Le texte (valeurs, libellés) reste en encre noire ou grise, jamais dans la couleur d'une série."),
            html.Li("Jamais deux axes verticaux différents sur un même graphique : on fait deux graphiques."),
            html.Li("Barres fines aux bouts arrondis, lignes de 2 px, grille discrète : la donnée seule est « forte »."),
            html.Li("Chaque graphique a des infobulles, et les filtres sont dans une barre au-dessus des graphiques."),
            html.Li("La période Covid est toujours signalée (zone_covid()), et les années incomplètes sont indiquées."),
        ], className="ds-list"), className="mb-4"),
    ])
