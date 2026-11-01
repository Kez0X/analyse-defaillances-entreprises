"""Page d'accueil : présentation du projet et chiffres clés (tirés du cube)."""
import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import dcc, html

from design import ENCRE, SERIES, badge, carte, chiffre_cle, encadre, entete, graphe, nombre, zone_covid
from donnees import coupe

dash.register_page(__name__, path="/", name="Accueil", order=0, section="Exploration")

PAGES = [
    ("/vue-ensemble", "Vue d'ensemble", "Temps, territoires, secteurs, profils d'entreprises.", "Lucas", "Exploration"),
    ("/parcours", "Parcours des procédures", "Le graphe des étapes, du redressement à la clôture.", "Luka", "Graphe"),
    ("/reseaux", "Réseaux", "Secteurs et départements qui « souffrent ensemble », entreprises liées.", "Luka", "Graphes"),
    ("/profils", "Profils financiers", "ACP, clustering et t-SNE sur les ratios des entreprises.", "Luka", "Clustering"),
]


def courbe_annuelle():
    df = coupe("cube_principal", categorie="entrée en défaillance", annee=None)
    df = df.assign(annee=df["annee"].astype(int)).sort_values("annee")
    df = df[df["annee"].between(2008, 2025)]  # années complètes seulement
    fig = go.Figure(go.Scatter(
        x=df["annee"], y=df["nb_entreprises"], mode="lines+markers",
        line=dict(color=SERIES[0]), fill="tozeroy", fillcolor="rgba(42,120,214,0.10)",
        hovertemplate="%{x} : %{y:,.0f} entreprises<extra></extra>",
    ))
    fin = df.iloc[-1]
    fig.add_annotation(x=fin["annee"], y=fin["nb_entreprises"], text=nombre(fin["nb_entreprises"]),
                       showarrow=False, xanchor="left", xshift=10, font=dict(color=ENCRE["primaire"], size=12))
    fig.update_layout(margin=dict(l=8, r=48, t=16, b=8), showlegend=False,
                      yaxis=dict(rangemode="tozero"), xaxis=dict(dtick=2, range=[2007.6, 2025.4]))
    return zone_covid(fig)


def layout():
    par_annee = coupe("cube_principal", categorie="entrée en défaillance", annee=None).set_index("annee")
    total = coupe("cube_principal", categorie="entrée en défaillance")["nb_entreprises"].iloc[0]
    n2025, n2024, n2019 = (par_annee.loc[a, "nb_entreprises"] for a in ("2025", "2024", "2019"))
    taux = coupe("taux", annee=None).set_index("annee")["taux_pour_mille"]
    ecart_2019 = 100 * (n2025 - n2019) / n2019

    return html.Div([
        entete(
            "Les défaillances d'entreprises en France",
            "Ce dashboard croise trois sources publiques : les annonces de procédures collectives du BODACC, "
            "le répertoire des entreprises SIRENE et les ratios financiers déposés au greffe. Il applique les "
            "méthodes du cours : exploration, cube OLAP, graphes, clustering et réduction de dimension.",
            surtitre="Projet M2 · Analyse de données",
            badges=[badge("BODACC 2008-2026"), badge("SIRENE : 30 M d'entreprises"), badge("Ratios BCE / INPI")],
        ),
        dbc.Row([
            dbc.Col(chiffre_cle("Entreprises entrées en défaillance", nombre(total),
                                "jugements de fin 2007 à octobre 2026"), md=6, xl=3, className="mb-4"),
            dbc.Col(chiffre_cle("Entreprises défaillantes en 2025", nombre(n2025),
                                f"contre {nombre(n2024)} en 2024"), md=6, xl=3, className="mb-4"),
            dbc.Col(chiffre_cle("Par rapport à 2019", f"+{ecart_2019:.0f} %",
                                f"{nombre(n2019)} en 2019, avant le Covid",
                                evolution=("au-dessus d'avant crise", "up")), md=6, xl=3, className="mb-4"),
            dbc.Col(chiffre_cle("Taux de défaillance 2025", f"{taux['2025']:.1f} ‰".replace(".", ","),
                                f"des entreprises actives au 1er janvier · {taux['2009']:.1f} ‰ en 2009".replace(".", ",")),
                    md=6, xl=3, className="mb-4"),
        ]),
        dbc.Row([
            dbc.Col(carte(
                graphe("ac-courbe", courbe_annuelle(), hauteur=300),
                titre="Entreprises entrées en défaillance chaque année",
                description="Nombre d'entreprises distinctes (SIREN) ayant un jugement d'ouverture de redressement "
                            "ou de liquidation, ou une extension de procédure.",
                pied="Années complètes 2008-2025. Source : BODACC, cube OLAP.",
            ), lg=8, className="mb-4"),
            dbc.Col(carte(
                html.Ul([
                    html.Li("Une ligne = un événement BODACC pour une entreprise."),
                    html.Li("Défaillance = ouverture de redressement ou de liquidation judiciaire."),
                    html.Li("Taux = entreprises défaillantes / entreprises actives au 1er janvier (SIRENE)."),
                    html.Li("2026 s'arrête fin octobre, 2020-2021 sont marquées par le Covid."),
                ], className="ds-list"),
                titre="À savoir pour lire les chiffres",
            ), lg=4, className="mb-4"),
        ]),
        html.H2("Les pages du dashboard", style={"fontSize": "18px", "fontWeight": 650, "margin": "8px 0 16px"}),
        dbc.Row([
            dbc.Col(dcc.Link(carte(
                html.Div([badge(type_, "accent")], style={"marginBottom": "10px"}),
                html.H3(nom, className="ds-card__title"),
                html.P(texte, className="ds-card__description"),
                html.Div(f"Responsable : {qui}", className="ds-link-card__owner"),
            ), href=href, className="ds-link-card"), md=6, xl=3, className="mb-4")
            for href, nom, texte, qui, type_ in PAGES
        ]),
        encadre("La page « Prédiction » est un bonus : la classification supervisée n'est pas au programme du cours.",
                titre="Bonus."),
    ])
