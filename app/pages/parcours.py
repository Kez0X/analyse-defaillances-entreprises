"""Parcours des procédures (axe 6) — page de Luka.

Données : notebooks/axes/parcours.ipynb -> data/dashboard/parcours_*.parquet
"""
import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import Input, Output, callback, dcc, html

import pandas as pd

from design import (AUTRE, ENCRE, GRIS_FRANCE, SERIES, badge, carte, encart_perimetre, entete, filtre, filtres, graphe,
                    gris_sauf, methode, nombre, pct, question, tableau, zoom)
from donnees import (TOUS, delais_perimetre, est_filtre, filtrer, issues_redressements, libelle_perimetre, lire,
                     part_liquidation_directe)

dash.register_page(__name__, path="/parcours", name="Parcours des procédures", order=3, section="Analyses")

COULEUR_ETAPE = {
    "Sauvegarde": SERIES[3], "Redressement judiciaire": SERIES[0], "Liquidation judiciaire": SERIES[0],
    "Plan de sauvegarde": SERIES[2], "Plan de redressement": SERIES[2], "Plan de cession": SERIES[2],
    "Fin de procédure (sauvée)": SERIES[2], "Clôture : extinction du passif": SERIES[2],
    "Clôture : insuffisance d'actif": AUTRE,
}


def figure_graphe(seuil):
    noeuds = lire("parcours_noeuds").set_index("etape")
    aretes = lire("parcours_aretes")
    aretes = aretes[aretes["entreprises"] >= seuil]
    fig = go.Figure()
    maxi = aretes["entreprises"].max()
    for _, a in aretes.iterrows():
        x0, y0 = noeuds.loc[a["source"], ["x", "y"]]
        x1, y1 = noeuds.loc[a["cible"], ["x", "y"]]
        largeur = 1 + 11 * (a["entreprises"] / maxi) ** 0.5
        fig.add_annotation(x=x1, y=y1, ax=x0, ay=y0, xref="x", yref="y", axref="x", ayref="y", showarrow=True,
                           arrowhead=2, arrowsize=0.6, arrowwidth=largeur, arrowcolor="rgba(137,135,129,0.40)",
                           standoff=22, startstandoff=22)
        # point invisible au milieu de la flèche, pour l'infobulle
        fig.add_trace(go.Scatter(
            x=[(x0 + x1) / 2], y=[(y0 + y1) / 2], mode="markers", marker=dict(size=14, opacity=0),
            hovertext=f"{a['source']} → {a['cible']}<br>{nombre(a['entreprises'])} entreprises"
                      f" ({100 * a['part_des_departs']:.1f} % des départs)<br>délai médian : {a['delai_median_mois']:.1f} mois",
            hoverinfo="text", showlegend=False))
    taille = 22 + 50 * noeuds["pagerank"] / noeuds["pagerank"].max()
    fig.add_trace(go.Scatter(
        x=noeuds["x"], y=noeuds["y"], mode="markers+text", text=noeuds.index, textposition="bottom center",
        textfont=dict(size=11, color=ENCRE["secondaire"]),
        marker=dict(size=taille, color=[COULEUR_ETAPE[e] for e in noeuds.index], line=dict(width=2, color="#fcfcfb")),
        hovertext=[f"<b>{e}</b><br>arrivées : {nombre(r['entrées (entreprises)'])}<br>départs : "
                   f"{nombre(r['sorties (entreprises)'])}<br>PageRank : {r['pagerank']:.3f}" for e, r in noeuds.iterrows()],
        hoverinfo="text", showlegend=False))
    fig.update_layout(xaxis=dict(visible=False, range=[-0.5, 3.6]), yaxis=dict(visible=False, range=[-1.5, 3.0]),
                      margin=dict(l=8, r=8, t=8, b=8))
    return fig


def figure_cohortes():
    c = lire("parcours_cohortes_rj")
    an = "année d'ouverture"
    fig = go.Figure()
    for issue, couleur in [("liquidation", SERIES[1]), ("plan ou sauvetage", SERIES[2]),
                           ("plan de cession", SERIES[0]), ("pas encore d'issue", AUTRE)]:
        fig.add_trace(go.Scatter(x=c[an], y=c[issue], mode="lines+markers", name=issue, line=dict(color=couleur),
                                 hovertemplate=f"{issue} : %{{y:.1f}} %<extra>%{{x}}</extra>"))
    fig.add_vrect(x0=2019.5, x1=2021.5, fillcolor=ENCRE["discrete"], opacity=0.08, line_width=0,
                  annotation_text="Covid", annotation_position="top left",
                  annotation_font=dict(size=11, color=ENCRE["discrete"]))
    fig.update_layout(yaxis=dict(title="% des redressements ouverts", rangemode="tozero"), xaxis=dict(dtick=2),
                      hovermode="x unified", margin=dict(t=40))
    return fig


ISSUES = ["liquidation", "plan ou sauvetage", "plan de cession", "pas encore d'issue"]
PASSAGES = ["Redressement judiciaire → Liquidation judiciaire", "Redressement judiciaire → Plan de cession",
            "Redressement judiciaire → Plan de redressement", "Sauvegarde → Plan de sauvegarde",
            "Liquidation judiciaire → Clôture : insuffisance d'actif", "Plan de redressement → Liquidation judiciaire"]


def repere_france(fig, x, y, horizontal=True):
    """Ajoute la valeur nationale en trait gris, à côté de la barre du périmètre."""
    fig.add_trace(go.Scatter(x=x, y=y, mode="markers", name="France",
                             marker=dict(symbol="line-ns" if horizontal else "line-ew", size=22,
                                         line=dict(width=3, color=ENCRE["secondaire"])),
                             hovertemplate="France : %{" + ("x" if horizontal else "y") + ":.1f}<extra></extra>"))
    fig.update_layout(showlegend=True, legend=dict(orientation="h", y=1.14, x=0))


def figure_issues(secteur=TOUS, region=TOUS):
    moy, _ = issues_redressements(secteur, region)
    moy = moy.reindex(ISSUES).fillna(0).sort_values()
    fig = go.Figure(go.Bar(x=moy.values, y=moy.index, orientation="h", name=libelle_perimetre(secteur, region),
                           marker_color=gris_sauf(len(moy), [list(moy.index).index("liquidation")], couleur=SERIES[1]),
                           text=[f"{v:.0f} %" for v in moy.values], textposition="outside", cliponaxis=False,
                           textfont=dict(color=ENCRE["secondaire"]),
                           hovertemplate="%{y} : %{x:.1f} % des redressements<extra></extra>"))
    if est_filtre(secteur, region):
        fr, _ = issues_redressements(TOUS, TOUS)
        repere_france(fig, fr.reindex(moy.index).values, moy.index)
    fig.update_layout(xaxis=dict(title="% des redressements ouverts de 2008 à 2023", range=[0, 100]),
                      yaxis=dict(showgrid=False), margin=dict(t=32, r=30))
    return fig


def figure_delais(secteur=TOUS, region=TOUS):
    def delais(sec, reg):
        a = delais_perimetre(sec, reg)
        a = a.assign(passage=a["étape"].astype(str) + " → " + a["suivante"].astype(str))
        return a[a["passage"].isin(PASSAGES) & (a["entreprises"] >= 10)].set_index("passage")
    fr = delais(TOUS, TOUS).sort_values("delai_median_mois")
    a = delais(secteur, region).reindex(fr.index)
    lib = a.index.str.replace("Redressement judiciaire", "Redressement").str.replace("Liquidation judiciaire", "Liquidation") \
                 .str.replace("Clôture : insuffisance d'actif", "Clôture")
    fig = go.Figure(go.Bar(x=a["delai_median_mois"], y=lib, orientation="h", name=libelle_perimetre(secteur, region),
                           marker_color=gris_sauf(len(a), [i for i, p in enumerate(a.index)
                                                            if p in PASSAGES[:1] + PASSAGES[-1:]]),
                           text=[("—" if v != v else f"{v:.1f} mois".replace(".", ",")) for v in a["delai_median_mois"]],
                           textposition="outside", cliponaxis=False, textfont=dict(color=ENCRE["secondaire"]),
                           customdata=a["entreprises"],
                           hovertemplate="%{y} : %{x:.1f} mois en médiane (%{customdata:,.0f} entreprises)<extra></extra>"))
    if est_filtre(secteur, region):
        repere_france(fig, fr["delai_median_mois"].values, lib)
    fig.update_layout(xaxis=dict(title="délai médian (mois)", range=[0, 40]), yaxis=dict(showgrid=False),
                      margin=dict(t=32, r=40))
    return fig


def sauves_par_annee(secteur, region, minimum=30):
    c = filtrer(lire("parcours_cohortes_perimetre"), secteur, region)
    c = c[c["année d'ouverture"].between(2008, 2023)]
    t = c.pivot_table(index="année d'ouverture", columns=c["issue à 36 mois"].astype(str), values="entreprises",
                      aggfunc="sum", fill_value=0)
    n = t.sum(axis=1)
    return (100 * t.get("plan ou sauvetage", 0) / n).where(n >= minimum), n


def figure_chances(secteur=TOUS, region=TOUS):
    filtre_actif = est_filtre(secteur, region)
    fr, _ = sauves_par_annee(TOUS, TOUS)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=fr.index, y=fr.values, mode="lines+markers", name="France",
                             line=dict(color=GRIS_FRANCE if filtre_actif else SERIES[2], width=2 if filtre_actif else 3),
                             hovertemplate="France, %{x} : %{y:.1f} %<extra></extra>"))
    if filtre_actif:
        p, n = sauves_par_annee(secteur, region)
        fig.add_trace(go.Scatter(x=p.index, y=p.values, mode="lines+markers", name=libelle_perimetre(secteur, region),
                                 line=dict(color=SERIES[2], width=3), customdata=n.values,
                                 hovertemplate="%{x} : %{y:.1f} % (%{customdata} redressements)<extra></extra>"))
        fig.update_layout(showlegend=True, legend=dict(orientation="h", y=1.14, x=0), hovermode="x unified")
    else:
        fig.add_annotation(x=2016, y=21.5, text="≈ 22 %", showarrow=False, yshift=16, font=dict(size=12, color=ENCRE["primaire"]))
        fig.add_annotation(x=2022, y=16.6, text="≈ 17 %", showarrow=False, yshift=-18, font=dict(size=12, color=ENCRE["primaire"]))
        fig.update_layout(showlegend=False)
    fig.add_vrect(x0=2019.5, x1=2021.5, fillcolor=ENCRE["discrete"], opacity=0.08, line_width=0,
                  annotation_text="Covid", annotation_position="top left",
                  annotation_font=dict(size=11, color=ENCRE["discrete"]))
    fig.update_layout(yaxis=dict(title="% des redressements sauvés (plan ou sauvetage)", rangemode="tozero"),
                      xaxis=dict(dtick=2), margin=dict(t=48))
    return fig


@callback(Output("pa-issues", "figure"), Output("pa-delais", "figure"), Output("pa-chances", "figure"),
          Output("pa-zoom-1", "children"), Output("pa-zoom-2", "children"), Output("pa-zoom-3", "children"),
          Input("filtre-secteur", "value"), Input("filtre-region", "value"))
def maj_parcours(secteur, region):
    figures = figure_issues(secteur, region), figure_delais(secteur, region), figure_chances(secteur, region)
    if not est_filtre(secteur, region):
        return *figures, None, None, None
    lib = libelle_perimetre(secteur, region)
    lj, n_ouv = part_liquidation_directe(secteur, region)
    iss, n_rj = issues_redressements(secteur, region)
    prudence = (f"Seulement {nombre(n_rj)} redressements dans ce périmètre : à lire avec prudence." if n_rj < 200 else None)
    z1 = encart_perimetre(lib, html.B(pct(lj)), " des entreprises sont liquidées directement (France : 68 %), et ",
                          html.B(pct(iss.get("liquidation", float("nan")))), " des redressements finissent en liquidation "
                          "(France : 70 %).", prudence=prudence)
    d = delais_perimetre(secteur, region).set_index(["étape", "suivante"])["delai_median_mois"]
    rj_lj = d.get(("Redressement judiciaire", "Liquidation judiciaire"), float("nan"))
    plan_lj = d.get(("Plan de redressement", "Liquidation judiciaire"), float("nan"))
    fmt = lambda v: "—" if v != v else f"{v:.1f} mois".replace(".", ",")
    z2 = encart_perimetre(lib, "Redressement → liquidation : ", html.B(fmt(rj_lj)), " (France : 2,8 mois) ; plan → "
                          "liquidation : ", html.B(fmt(plan_lj)), " (France : 27 mois).")
    p, _ = sauves_par_annee(secteur, region)
    avant = issues_redressements(secteur, region, range(2013, 2021))[0].get("plan ou sauvetage", float("nan"))
    apres = issues_redressements(secteur, region, range(2021, 2024))[0].get("plan ou sauvetage", float("nan"))
    z3 = encart_perimetre(lib, "Redressements sauvés : ", html.B(pct(avant)), " en 2013-2020, ",
                          html.B(pct(apres)), " en 2021-2023 (France : 22 % puis 17 %).",
                          prudence="Années à moins de 30 redressements non tracées." if p.isna().any() else None)
    return *figures, z1, z2, z3


def layout():
    transitions = (lire("parcours_aretes").sort_values("entreprises", ascending=False).head(12)
                   .assign(passage=lambda d: d["source"].astype(str) + " → " + d["cible"].astype(str),
                           entreprises=lambda d: d["entreprises"].map(nombre),
                           part=lambda d: (100 * d["part_des_departs"]).map(lambda v: f"{v:.1f} %".replace(".", ",")),
                           delai=lambda d: d["delai_median_mois"].map(lambda v: f"{v:.1f}".replace(".", ",")))
                   [["passage", "entreprises", "part", "delai"]]
                   .rename(columns={"part": "part des départs", "delai": "délai médian (mois)"}))
    top_tab = lire("parcours_top").head(10).assign(entreprises=lambda d: d["entreprises"].map(nombre))

    return html.Div([
        entete("Le parcours des procédures",
               "Que se passe-t-il une fois qu'une entreprise entre en procédure collective ? On a reconstitué le parcours "
               "de 918 171 entreprises au BODACC, de l'ouverture jusqu'à l'issue.",
               surtitre="Analyses", badges=[badge("Graphe orienté", "accent"), badge("Responsable : Luka")]),
        question("Une entreprise en procédure peut-elle s'en sortir ?",
                 [html.B("Rarement. "), html.B("2 entreprises sur 3"), " sont liquidées directement, sans tentative de "
                  "sauvetage. Et quand on tente un redressement, ", html.B("7 sur 10 finissent quand même en liquidation"),
                  " dans les 36 mois. Seulement 1 sur 5 obtient un plan ou est sauvée."],
                 zoom("pa-zoom-1"),
                 carte(graphe("pa-issues", hauteur=280),
                       titre="Ce que deviennent les redressements, 36 mois après l'ouverture",
                       pied="Moyenne des redressements ouverts de 2008 à 2023 (ceux qui ont 36 mois de recul)."),
                 numero=1),
        question("Combien de temps a-t-on pour la sauver ?",
                 [html.B("Très peu. "), "Quand un redressement échoue, la liquidation tombe en ",
                  html.B("2,8 mois"), " en médiane : à la fin de la période d'observation. Et quand un plan est adopté "
                  "puis échoue, c'est en général ", html.B("au bout de 2 ans"), " (27 mois)."],
                 zoom("pa-zoom-2"),
                 carte(graphe("pa-delais", hauteur=320), titre="Délai médian entre deux étapes"),
                 numero=2),
        question("Le Covid a-t-il changé les chances de s'en sortir ?",
                 [html.B("Oui, en mal. "), "La part des redressements qui obtiennent un plan ou sont sauvés est passée "
                  "d'environ ", html.B("22 % (2013-2020) à environ 17 % (2021-2023)"), "."],
                 zoom("pa-zoom-3"),
                 carte(graphe("pa-chances", hauteur=340),
                       titre="Part des redressements sauvés, selon l'année d'ouverture"),
                 numero=3),
        methode(
            filtres(filtre("Passages affichés", dcc.Dropdown(
                options=[{"label": f"au moins {nombre(s)} entreprises", "value": s} for s in [100, 500, 2000, 10000]],
                value=500, id="pa-seuil", clearable=False))),
            carte(graphe("pa-graphe", hauteur=560), titre="Le graphe orienté des étapes",
                  description="Épaisseur des flèches = nombre d'entreprises ; taille des étapes = PageRank. Bleu : "
                              "ouverture ; jaune : sauvegarde ; vert : l'entreprise continue ou paie ses dettes ; gris : "
                              "clôture pour insuffisance d'actif. Survoler une étape ou le milieu d'une flèche.",
                  pied="Entreprises avec SIREN dont le premier événement est une ouverture (2008-2026). Jugements "
                       "« fourre-tout » (2,2 %) écartés.", className="mb-4"),
            dbc.Row([
                dbc.Col(carte(tableau(transitions), titre="Les passages les plus fréquents"), lg=7, className="mb-4"),
                dbc.Col(carte(tableau(top_tab), titre="Les parcours complets les plus fréquents"), lg=5, className="mb-4"),
            ]),
            carte(graphe("pa-cohortes", figure_cohortes(), hauteur=360),
                  titre="Toutes les issues des redressements, par année d'ouverture",
                  pied="Priorité : plan de cession, puis liquidation, puis plan ou sauvetage."),
        ),
    ])


@callback(Output("pa-graphe", "figure"), Input("pa-seuil", "value"))
def maj_graphe(seuil):
    return figure_graphe(seuil)
