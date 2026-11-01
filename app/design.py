"""
Design system du dashboard, côté Python.

- les couleurs (mêmes valeurs que les variables CSS de assets/design_system.css) ;
- le thème plotly « defaillances », appliqué par défaut à tous les graphiques ;
- les composants réutilisables : en-tête de page, carte, chiffre clé, barre de filtres, badge, encadré.

Règles à respecter (voir docs/dashboard.md) :
- les couleurs des séries suivent un ORDRE FIXE et restent attachées à la même chose
  (une catégorie d'événement garde toujours sa couleur, même si on filtre) ;
- les couleurs de statut (vert, orange, rouge) ne servent jamais pour une série ;
- un graphique avec 2 séries ou plus a toujours une légende ;
- le texte reste en encre (noir / gris), jamais dans la couleur d'une série.
"""
from __future__ import annotations

import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.io as pio
from dash import dcc, html

# --------------------------------------------------------------------------- couleurs
ENCRE = {"primaire": "#0b0b0b", "secondaire": "#52514e", "discrete": "#898781"}
SURFACE = {"page": "#f4f4f1", "carte": "#fcfcfb", "retrait": "#efeeea"}
LIGNES = {"grille": "#e1e0d9", "axe": "#c3c2b7"}
ACCENT = "#2a78d6"

# Séries catégorielles : ordre fixe, validé pour le daltonisme (5 premières couleurs)
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
AUTRE = "#b5b3ab"  # « autre » / non renseigné : un gris neutre, jamais une couleur de série

# Chaque catégorie d'événement garde toujours la même couleur
COULEURS_CATEGORIES = {
    "entrée en défaillance": SERIES[0],
    "aggravation": SERIES[1],
    "issue": SERIES[2],
    "signal précoce": SERIES[3],
    "autre": AUTRE,
}

# Échelle séquentielle (une seule teinte, du clair au foncé) : cartes, matrices
SEQUENTIELLE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
# Échelle divergente (bleu ↔ gris ↔ rouge) : écarts à une moyenne
DIVERGENTE = ["#184f95", "#3987e5", "#9ec5f4", "#f0efec", "#f2a3a2", "#e34948", "#a12d2d"]

# Statut : réservé aux états (bon / attention / grave / critique), toujours avec un libellé
STATUT = {"bon": "#0ca30c", "attention": "#fab219", "grave": "#ec835a", "critique": "#d03b3b"}

# --------------------------------------------------------------------------- thème plotly
POLICE = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'

_axe = dict(
    gridcolor=LIGNES["grille"], gridwidth=1, griddash="solid",
    linecolor=LIGNES["axe"], linewidth=1, showline=True,
    zeroline=False, ticks="", tickfont=dict(color=ENCRE["discrete"], size=12),
    title=dict(font=dict(color=ENCRE["secondaire"], size=12), standoff=12),
    automargin=True,
)

pio.templates["defaillances"] = go.layout.Template(
    layout=dict(
        font=dict(family=POLICE, color=ENCRE["secondaire"], size=13),
        title=dict(font=dict(family=POLICE, color=ENCRE["primaire"], size=15), x=0, xanchor="left", y=0.97),
        paper_bgcolor=SURFACE["carte"],
        plot_bgcolor=SURFACE["carte"],
        colorway=SERIES,
        xaxis={**_axe, "showgrid": False},
        yaxis={**_axe, "showline": False},
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    font=dict(color=ENCRE["secondaire"], size=12), title=dict(text="")),
        hoverlabel=dict(bgcolor="#ffffff", bordercolor=LIGNES["grille"],
                        font=dict(family=POLICE, color=ENCRE["primaire"], size=13)),
        margin=dict(l=8, r=8, t=48, b=8),
        bargap=0.45,            # barres fines : on laisse de l'air
        barcornerradius=4,      # bout de barre arrondi
        separators=", ",        # virgule décimale, espace des milliers
        colorscale=dict(sequential=[[i / (len(SEQUENTIELLE) - 1), c] for i, c in enumerate(SEQUENTIELLE)],
                        diverging=[[i / (len(DIVERGENTE) - 1), c] for i, c in enumerate(DIVERGENTE)]),
    ),
    data=dict(
        scatter=[go.Scatter(line=dict(width=2), marker=dict(size=8, line=dict(width=2, color=SURFACE["carte"])))],
        bar=[go.Bar(marker=dict(line=dict(width=0)))],
    ),
)
pio.templates.default = "defaillances"


ANNEES_INCOMPLETES = {2007: "fin d'année seulement", 2026: "jusqu'à fin octobre"}


def couleurs_annees(annees, couleur):
    """Une couleur par barre : pâle pour les années incomplètes (2007, 2026), pleine sinon."""
    r, g, b = (int(couleur[i:i + 2], 16) for i in (1, 3, 5))
    return [f"rgba({r},{g},{b},0.35)" if a in ANNEES_INCOMPLETES else couleur for a in annees]


def zone_covid(fig, x0=2019.5, x1=2021.5):
    """Grise la période Covid sur un axe d'années (rupture à toujours signaler)."""
    fig.add_vrect(x0=x0, x1=x1, fillcolor=ENCRE["discrete"], opacity=0.08, line_width=0,
                  annotation_text="Covid", annotation_position="top left",
                  annotation_font=dict(size=11, color=ENCRE["discrete"]))
    return fig


def graphe(id_, figure=None, hauteur=360):
    """Un dcc.Graph aux réglages du design system."""
    return dcc.Graph(id=id_, figure=figure or {}, style={"height": f"{hauteur}px"},
                     config={"displaylogo": False, "locale": "fr",
                             "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"]})


# --------------------------------------------------------------------------- composants
def badge(texte, variante=None, couleur=None):
    """Petite pastille. variante : None, 'accent', 'warning'. couleur : un point de couleur devant."""
    classes = "ds-badge" + (f" ds-badge--{variante}" if variante else "")
    contenu = [html.Span(className="ds-badge__dot", style={"background": couleur})] if couleur else []
    return html.Span([*contenu, texte], className=classes)


def entete(titre, sous_titre=None, surtitre=None, badges=None):
    """En-tête de page : surtitre (rubrique), titre, phrase d'introduction, badges."""
    return html.Div([
        html.Div(surtitre, className="ds-page-header__eyebrow") if surtitre else None,
        html.H1(titre, className="ds-page-header__title"),
        html.P(sous_titre, className="ds-page-header__subtitle") if sous_titre else None,
        html.Div(badges, className="ds-page-header__badges") if badges else None,
    ], className="ds-page-header")


def carte(*enfants, titre=None, description=None, pied=None, action=None, className=""):
    """Carte blanche : le contenant de base (graphique, tableau, texte)."""
    tete = None
    if titre or action:
        tete = html.Div([
            html.Div([
                html.H3(titre, className="ds-card__title") if titre else None,
                html.P(description, className="ds-card__description") if description else None,
            ]),
            action,
        ], className="ds-card__header")
    return html.Div([tete, *enfants, html.Div(pied, className="ds-card__footer") if pied else None],
                    className=f"ds-card {className}".strip())


def chiffre_cle(libelle, valeur, detail=None, evolution=None):
    """Chiffre clé (stat tile). evolution : (texte, 'up' | 'down') ; up = plus de défaillances."""
    delta = None
    if evolution:
        texte, sens = evolution
        delta = html.Span([("▲ " if sens == "up" else "▼ ") + texte],
                          className=f"ds-stat__delta ds-stat__delta--{sens}")
    return carte(
        html.Div(libelle, className="ds-stat__label"),
        html.Div(valeur, className="ds-stat__value"),
        html.Div(delta) if delta else None,
        html.Div(detail, className="ds-stat__detail") if detail else None,
    )


def filtres(*champs):
    """Barre de filtres, toujours au-dessus des graphiques qu'elle pilote."""
    return html.Div(list(champs), className="ds-filters")


def filtre(libelle, controle):
    """Un champ de la barre de filtres : un libellé + un contrôle (Dropdown, RadioItems…)."""
    return html.Div([html.Span(libelle, className="ds-filter__label"), controle], className="ds-filter")


def boutons_segmentes(id_, options, valeur):
    """Choix exclusif court (2 à 4 options), affiché comme des onglets."""
    return dbc.RadioItems(id=id_, options=options, value=valeur, inline=True, className="ds-segmented")


def encadre(texte, titre=None, variante="info"):
    """Encadré : note (info) ou mise en garde (warning)."""
    return html.Div([
        html.Div(className="ds-callout__bar"),
        html.Div([html.Span(titre + " ", className="ds-callout__title") if titre else None, texte]),
    ], className=f"ds-callout ds-callout--{variante}")


def en_construction(titre, surtitre, axes, methodes, auteur):
    """Page provisoire : dit ce qui viendra ici, en attendant les analyses."""
    return html.Div([
        entete(titre, surtitre=surtitre,
               badges=[badge("En construction", "warning"), badge(f"Responsable : {auteur}")]),
        dbc.Row([
            dbc.Col(carte(html.Ul([html.Li(a) for a in axes], className="ds-list"),
                          titre="Ce qui viendra ici"), lg=7, className="mb-4"),
            dbc.Col(carte(html.Ul([html.Li(m) for m in methodes], className="ds-list"),
                          titre="Méthodes"), lg=5, className="mb-4"),
        ]),
    ])


def nombre(n):
    """12345 -> '12 345' (espace insécable des milliers)."""
    return f"{n:,.0f}".replace(",", " ")
