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


# --------------------------------------------------------------------------- graphiques partagés
def couleur_groupe(i):
    """Couleur du groupe / de la communauté n° i (1, 2, 3…), dans l'ordre fixe des séries."""
    return SERIES[(int(i) - 1) % len(SERIES)]


def figure_reseau(noeuds, aretes, x, y, groupe, taille, survol, source="source", cible="cible",
                  libelle_groupe="Communauté", texte=None, taille_max=34):
    """Réseau plotly : arêtes grises en fond, nœuds colorés par groupe (une trace par groupe = une légende).

    noeuds : DataFrame avec l'identifiant en index, les colonnes x, y, groupe, taille et survol (texte de l'infobulle).
    aretes : DataFrame avec les colonnes source et cible (identifiants des nœuds).
    texte  : colonne à écrire à côté des nœuds (None = aucun texte).
    """
    pos = noeuds[[x, y]]
    a = aretes[aretes[source].isin(pos.index) & aretes[cible].isin(pos.index)]
    xs, ys = [], []
    for u, v in zip(a[source], a[cible]):
        xs += [pos.at[u, x], pos.at[v, x], None]
        ys += [pos.at[u, y], pos.at[v, y], None]
    fig = go.Figure(go.Scatter(x=xs, y=ys, mode="lines", line=dict(width=0.6, color="rgba(137,135,129,0.28)"),
                               hoverinfo="skip", showlegend=False))
    t = noeuds[taille]
    tailles = 8 + (taille_max - 8) * (t - t.min()) / max(t.max() - t.min(), 1e-9)
    for g in sorted(noeuds[groupe].dropna().unique()):
        m = noeuds[groupe] == g
        fig.add_trace(go.Scatter(
            x=noeuds.loc[m, x], y=noeuds.loc[m, y], mode="markers+text" if texte else "markers",
            text=noeuds.loc[m, texte] if texte else None, textposition="top center",
            textfont=dict(size=10, color=ENCRE["secondaire"]),
            marker=dict(size=tailles[m], color=couleur_groupe(g), line=dict(width=1.5, color=SURFACE["carte"])),
            hovertext=noeuds.loc[m, survol], hoverinfo="text", name=f"{libelle_groupe} {int(g)}"))
    fig.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False), margin=dict(l=8, r=8, t=40, b=8),
                      hovermode="closest")
    return fig


def tableau(df, id_=None, hauteur=None):
    """Tableau simple aux couleurs du design system."""
    import dash_bootstrap_components as dbc
    return html.Div(dbc.Table.from_dataframe(df, striped=False, bordered=False, hover=True, size="sm",
                                             className="ds-table", style={"fontSize": "13px"}),
                    className="ds-table-wrap")


# --------------------------------------------------------------------------- questions et réponses
def question(titre, reponse, *contenu, id_=None, numero=None):
    """Un bloc « question → réponse → preuve » : la question en titre, la réponse mise en avant, puis le graphique."""
    options = {"id": id_} if id_ else {}
    return html.Section([
        html.Div([
            html.Span(f"Question {numero}" if numero else "Question", className="ds-question__label"),
            html.H2(titre, className="ds-question__titre"),
        ]),
        html.P(reponse, className="ds-question__reponse"),
        *contenu,
    ], className="ds-question", **options)


def methode(*contenu, titre="Comment on l'a obtenu"):
    """Bloc repliable pour le détail technique (fermé par défaut)."""
    return html.Details([html.Summary(titre, className="ds-methode__titre"), html.Div(contenu, className="ds-methode__corps")],
                        className="ds-methode")


def reponse_cle(texte, lien, libelle_lien):
    """Une carte de l'accueil : une réponse courte et le lien vers la page qui la démontre."""
    return dcc.Link(html.Div([
        html.P(texte, className="ds-retenir__texte"),
        html.Span(libelle_lien + " →", className="ds-retenir__lien"),
    ], className="ds-card ds-retenir"), href=lien, className="ds-link-card")


def gris_sauf(n, indices, couleur=ACCENT, fond="#d6d4cc"):
    """Liste de couleurs : tout en gris, sauf les éléments à mettre en évidence."""
    return [couleur if i in indices else fond for i in range(n)]


# --------------------------------------------------------------------------- périmètre (filtres globaux)
GRIS_FRANCE = "#b5b3ab"  # la référence nationale, en gris, quand un périmètre est choisi


def zoom(id_):
    """Emplacement, sous la réponse nationale, du texte « dans votre périmètre » (rempli par un callback)."""
    return html.Div(id=id_)


def encart_perimetre(libelle, *texte, prudence=None):
    """Le texte « dans votre périmètre ». prudence : message si les effectifs sont trop petits pour conclure."""
    return html.Div([html.Span(libelle, className="ds-zoom__label"), *texte,
                     html.Div(prudence, style={"marginTop": "4px", "color": ENCRE["secondaire"]}) if prudence else None],
                    className="ds-zoom ds-zoom--prudence" if prudence else "ds-zoom")


def pct(v, decimales=0):
    if v != v:  # NaN : pas assez de données
        return "—"
    return f"{v:.{decimales}f} %".replace(".", ",")


def pour_mille(v):
    if v != v:
        return "—"
    return f"{v:.1f} ‰".replace(".", ",")
