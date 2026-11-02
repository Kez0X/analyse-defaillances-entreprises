"""Événements de masse — page de Luka.

Données : notebooks/axes/evenements.ipynb -> data/dashboard/evenements_*.parquet (+ taux et séries du cube)
"""
import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
from dash import html

from dash import Input, Output, callback

from design import (ACCENT, AUTRE, ENCRE, GRIS_FRANCE, SERIES, badge, carte, encart_perimetre, entete, graphe,
                    gris_sauf, methode, nombre, pct, pour_mille, question, tableau, zoom)
from donnees import (TOUS, bilan_rattrapage, est_filtre, libelle_perimetre, lire, serie_perimetre, taux_perimetre)

dash.register_page(__name__, path="/evenements", name="Événements de masse", order=2, section="Analyses")


def figure_indice(secteur=TOUS, region=TOUS):
    filtre_actif = est_filtre(secteur, region)
    m = serie_perimetre(TOUS, TOUS)
    dates = pd.to_datetime(m.index)
    fig = go.Figure()
    fig.add_hrect(y0=75, y1=125, fillcolor="#e1e0d9", opacity=0.35, line_width=0)
    fig.add_vrect(x0="2020-01-01", x1="2022-08-31", fillcolor=ACCENT, opacity=0.10, line_width=0,
                  annotation_text="Covid : 32 mois sous la normale", annotation_position="top left",
                  annotation_font=dict(size=12, color=ENCRE["primaire"]))
    fig.add_trace(go.Scatter(x=dates, y=m["indice"], mode="lines", name="France",
                             line=dict(color=GRIS_FRANCE if filtre_actif else ACCENT, width=1.5 if filtre_actif else 2),
                             customdata=m[["entrees", "reference"]],
                             hovertemplate="France : indice %{y:.0f} (%{customdata[0]:,.0f} défaillances, normale "
                                           "%{customdata[1]:,.0f})<extra></extra>"))
    if filtre_actif:
        d = serie_perimetre(secteur, region)
        # moyenne sur 3 mois : un petit périmètre a peu de défaillances par mois, la courbe brute serait illisible
        lisse = 100 * d["entrees"].rolling(3).sum() / d["reference"].rolling(3).sum().where(lambda x: x > 0)
        fig.add_trace(go.Scatter(x=dates, y=lisse, mode="lines", name=libelle_perimetre(secteur, region),
                                 line=dict(color=ACCENT, width=2),
                                 hovertemplate="périmètre : indice %{y:.0f} (moyenne sur 3 mois)<extra></extra>"))
        haut = max(145, 1.1 * float(lisse.max())) if lisse.notna().any() else 145
        fig.update_layout(hovermode="x unified", showlegend=True, legend=dict(orientation="h", y=1.12, x=0),
                          yaxis=dict(range=[0, haut]))
    else:
        creux = m.loc[m["indice"].idxmin()]
        fig.add_annotation(x=pd.to_datetime(m["indice"].idxmin()), y=creux["indice"], text="avril 2020 : indice 27",
                           showarrow=True, arrowhead=0, ax=60, ay=10, font=dict(size=11, color=ENCRE["secondaire"]))
        fig.update_layout(showlegend=False)
    fig.update_layout(yaxis_title="indice (100 = mois normal)", margin=dict(t=48))
    if not filtre_actif:
        fig.update_layout(yaxis_range=[0, 145])
    return fig


def indice_annuel(secteur, region):
    d = serie_perimetre(secteur, region)
    a = d.groupby(d.index.str[:4])["indice"].mean()   # moyenne des indices mensuels, comme dans le notebook
    return a[a.index <= "2025"]


def figure_indice_annuel(secteur=TOUS, region=TOUS):
    a = indice_annuel(secteur, region)
    fig = go.Figure(go.Bar(x=a.index, y=a.values, name=libelle_perimetre(secteur, region),
                           marker_color=gris_sauf(len(a), [list(a.index).index(x) for x in ("2009", "2024", "2025")]),
                           hovertemplate="%{x} : indice moyen %{y:.0f}<extra></extra>"))
    if est_filtre(secteur, region):
        fr = indice_annuel(TOUS, TOUS)
        fig.add_trace(go.Scatter(x=fr.index, y=fr.values, mode="markers", name="France",
                                 marker=dict(symbol="line-ew", size=18, line=dict(width=2.5, color=ENCRE["secondaire"])),
                                 hovertemplate="France : %{y:.0f}<extra></extra>"))
        fig.update_layout(showlegend=True, legend=dict(orientation="h", y=1.12, x=0))
    fig.add_hline(y=100, line=dict(color=ENCRE["discrete"], width=1))
    fig.update_layout(yaxis=dict(title="indice de l'année (100 = normale)", rangemode="tozero"), margin=dict(t=32))
    return fig


def taux_annuels(secteur, region):
    return pd.Series({a: taux_perimetre(secteur, region, (str(a),)) for a in range(2008, 2026)})


def figure_taux(secteur=TOUS, region=TOUS):
    t = taux_annuels(secteur, region)
    fig = go.Figure(go.Bar(x=t.index, y=t.values, name=libelle_perimetre(secteur, region),
                           marker_color=gris_sauf(len(t), [list(t.index).index(x) for x in (2009, 2024, 2025)]),
                           hovertemplate="%{x} : %{y:.1f} ‰ des entreprises actives<extra></extra>"))
    if est_filtre(secteur, region):
        fr = taux_annuels(TOUS, TOUS)
        fig.add_trace(go.Scatter(x=fr.index, y=fr.values, mode="markers", name="France",
                                 marker=dict(symbol="line-ew", size=18, line=dict(width=2.5, color=ENCRE["secondaire"])),
                                 hovertemplate="France : %{y:.1f} ‰<extra></extra>"))
        fig.update_layout(showlegend=True, legend=dict(orientation="h", y=1.12, x=0))
    fig.update_layout(yaxis=dict(title="taux de défaillance (‰)", rangemode="tozero"), xaxis=dict(dtick=2), margin=dict(t=32))
    return fig


@callback(Output("ev-indice", "figure"), Output("ev-annuel", "figure"), Output("ev-taux", "figure"),
          Output("ev-zoom-1", "children"), Output("ev-zoom-2", "children"),
          Input("filtre-secteur", "value"), Input("filtre-region", "value"))
def maj_evenements(secteur, region):
    figures = figure_indice(secteur, region), figure_indice_annuel(secteur, region), figure_taux(secteur, region)
    if not est_filtre(secteur, region):
        return *figures, None, None
    lib = libelle_perimetre(secteur, region)
    b = bilan_rattrapage(secteur, region)
    def indice_covid(sec, reg):
        d = serie_perimetre(sec, reg).loc["2020-01":"2022-08"]
        return 100 * d["entrees"].sum() / d["reference"].sum() if d["reference"].sum() else float("nan")
    covid, covid_fr = indice_covid(secteur, region), indice_covid(TOUS, TOUS)
    d = serie_perimetre(secteur, region).loc["2020-01":"2022-08"]
    z1 = encart_perimetre(lib, "Pendant le Covid, ", html.B(f"{pct(abs(100 - covid))} de défaillances "
                                                            f"{'en moins' if covid < 100 else 'en plus'}"),
                          f" que la normale (France : {pct(100 - covid_fr)} en moins), soit {nombre(b['manquantes'])} défaillances "
                          "« manquantes ».",
                          prudence="Peu de défaillances par mois dans ce périmètre : la courbe est bruitée."
                          if d["reference"].mean() < 20 else None)
    a, t = indice_annuel(secteur, region), taux_annuels(secteur, region)
    a_fr, t_fr = indice_annuel(TOUS, TOUS), taux_annuels(TOUS, TOUS)
    z2 = encart_perimetre(lib, "En 2025, indice ", html.B(f"{a.get('2025', float('nan')):.0f}"),
                          f" (France : {a_fr['2025']:.0f}) et taux de ", html.B(pour_mille(t[2025])),
                          f" (France : {pour_mille(t_fr[2025])}). En 2009 : {pour_mille(t[2009])} "
                          f"(France : {pour_mille(t_fr[2009])}).")
    return *figures, z1, z2


def figure_secteur_66():
    s = lire("series_divisions_mois")["66"]
    s = s.loc["2015-01":"2026-10"]
    toute = lire("series_divisions_mois")["66"]
    ref = toute[toute.index.str[:4].isin([str(a) for a in range(2010, 2020)])]
    ref = ref.groupby(ref.index.str[5:]).mean()
    normale = s.index.str[5:].map(ref)
    dates = pd.to_datetime(s.index)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=normale, name="normale (même mois en 2010-2019)",
                             line=dict(color=AUTRE, width=2, dash="dot"), hovertemplate="normale : %{y:.0f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=dates, y=s.values, name="défaillances du mois", line=dict(color=ACCENT, width=2),
                             hovertemplate="%{x|%B %Y} : %{y:.0f} défaillances<extra></extra>"))
    fig.add_vrect(x0="2023-11-01", x1="2026-10-31", fillcolor=SERIES[1], opacity=0.08, line_width=0,
                  annotation_text="3 à 4 fois la normale", annotation_position="top left",
                  annotation_font=dict(size=12, color=ENCRE["primaire"]))
    fig.update_layout(yaxis=dict(title="entrées en défaillance par mois", rangemode="tozero"), hovermode="x unified",
                      margin=dict(t=40))
    return fig


def figure_journees():
    j = lire("evenements_jours")
    n = j.assign(annee=j["jour"].str[:4]).groupby("annee").size().reindex([str(a) for a in range(2008, 2027)], fill_value=0)
    fig = go.Figure(go.Bar(x=n.index, y=n.values, marker_color=gris_sauf(len(n), [list(n.index).index(x) for x in ("2023", "2024", "2025", "2026")]),
                           hovertemplate="%{x} : %{y} journées de masse<extra></extra>"))
    fig.add_annotation(x="2026", y=n["2026"], text="jusqu'à octobre", showarrow=False, yshift=14,
                       font=dict(size=10, color=ENCRE["discrete"]))
    fig.update_layout(yaxis=dict(title="journées de masse"), margin=dict(t=24))
    return fig


def layout():
    j = lire("evenements_jours").copy()
    grandes = (j.sort_values("entrees", ascending=False).head(8)
               .assign(jour=lambda d: pd.to_datetime(d["jour"]).dt.strftime("%d/%m/%Y"),
                       tribunal=lambda d: d["tribunal"].astype(str).str.replace("TRIBUNAL DE COMMERCE - ", "TC ")
                                                       .str.replace("TRIBUNAL JUDICIAIRE - ", "TJ "),
                       liquidations=lambda d: (100 * d["part_liquidation"]).round(0).astype(int).astype(str) + " %",
                       secteur=lambda d: d["secteur principal"].astype(str) + " (" +
                                         (100 * d["part du secteur principal"]).round(0).astype(int).astype(str) + " %)")
               [["jour", "tribunal", "entrees", "secteur", "liquidations"]]
               .rename(columns={"entrees": "entreprises", "secteur": "secteur principal"}))
    pics_s = lire("evenements_pics_secteurs")
    pics_d = lire("evenements_pics_departements")
    return html.Div([
        entete("Les événements de masse",
               "Les moments où les défaillances sortent nettement de la normale : pour tout le pays, pour un secteur, "
               "ou un seul jour dans un tribunal. La normale d'un mois, c'est la moyenne du même mois de 2010 à 2019.",
               surtitre="Analyses", badges=[badge("BODACC 2008-2026", "accent"), badge("Responsable : Luka")]),

        question("Y a-t-il eu de vrais chocs depuis 2008 ?",
                 [html.B("Un seul : le Covid. "), "De janvier 2020 à août 2022, il y a eu presque ",
                  html.B("deux fois moins de défaillances"), " que d'habitude, soit environ ",
                  html.B("68 000 défaillances « manquantes »"), ". Même la crise de 2009 reste dans la normale."],
                 zoom("ev-zoom-1"),
                 carte(graphe("ev-indice", hauteur=380),
                       pied="Bande grise : de 75 à 125, l'écart habituel d'un mois à l'autre. Source : BODACC."),
                 numero=1),

        question("La vague de 2024-2025 est-elle un record ?",
                 [html.B("En nombre, oui"), " : plus de 60 000 entreprises par an, le plus haut niveau depuis 2008. ",
                  html.B("Mais pas un choc"), " : c'est 13 à 14 % au-dessus de la normale, à peine plus qu'en 2009 "
                  "(+11 %). Et comme il y a deux fois plus d'entreprises qu'en 2008, le ",
                  html.B("taux de défaillance (3,8 ‰) reste bien plus bas qu'en 2009 (6,3 ‰)"), "."],
                 zoom("ev-zoom-2"),
                 dbc.Row([
                     dbc.Col(carte(graphe("ev-annuel", hauteur=300),
                                   titre="Comparé à la normale (indice moyen par an)"), lg=6, className="mb-3"),
                     dbc.Col(carte(graphe("ev-taux", hauteur=300),
                                   titre="Rapporté au nombre d'entreprises (taux par an)"), lg=6, className="mb-3"),
                 ]),
                 numero=2),

        question("Des secteurs ont-ils vécu leur propre crise ?",
                 [html.B("Oui, un seul : les auxiliaires de services financiers et d'assurance"),
                  " (courtiers, intermédiaires). Depuis novembre 2023, ils ont chaque mois ",
                  html.B("3 à 4 fois plus de défaillances"), " que d'habitude. Aucun autre secteur n'a connu de vague "
                  "comparable, même en 2009."],
                 carte(graphe("ev-66", figure_secteur_66(), hauteur=340),
                       titre="Auxiliaires de services financiers et d'assurance (NAF 66)",
                       pied=f"{len(pics_s)} mois-secteurs dépassent 3 fois la normale depuis 2008 : tous depuis fin 2023, "
                            f"dont {int((pics_s['cle'] == '66').sum())} pour ce secteur."),
                 numero=3),

        question("Les tribunaux jugent-ils en masse ?",
                 [html.B("De plus en plus. "), "Les journées où un seul tribunal prononce au moins 50 défaillances "
                  "sont passées de 0 à 6 par an (2011-2022) à ", html.B("22 en 2024 et 24 en 2025"), ". Les deux plus grandes, à ",
                  html.B("Lyon (190 puis 147 entreprises en un jour)"), ", concernent presque uniquement la construction "
                  "de bâtiments, toutes liquidées."],
                 dbc.Row([
                     dbc.Col(carte(graphe("ev-jours", figure_journees(), hauteur=320), titre="Journées de masse par an"),
                             lg=5, className="mb-3"),
                     dbc.Col(carte(tableau(grandes), titre="Les plus grandes journées",
                                   pied="Hypothèse : des groupes de promotion immobilière, dont chaque programme est une "
                                        "société à part, liquidés d'un coup."), lg=7, className="mb-3"),
                 ]),
                 numero=4),

        methode(
            html.Ul([
                html.Li("Normale d'un mois = moyenne du même mois de 2010 à 2019 (indice 100). Avec 2017-2019 seulement, "
                        "la normale était trop basse (les défaillances baissaient depuis 2015)."),
                html.Li("Mois anormal : indice sous 75 ou au-dessus de 125. Deux mois anormaux qui se suivent forment un épisode."),
                html.Li("Pic local : au moins 3 fois la normale, au moins 30 défaillances, et une normale d'au moins 10 "
                        "(sinon, un mois d'août où le tribunal siège peu donne des rapports absurdes)."),
                html.Li("Journée de masse : au moins 50 entrées en défaillance le même jour dans le même tribunal "
                        "(99 % des journées en ont moins de 31). Aucune ne vient d'une annonce collective."),
            ], className="ds-list"),
            dbc.Row([
                dbc.Col(carte(tableau(pics_d.assign(ratio=pics_d["ratio"].round(1), normale=pics_d["normale"].round(0))
                                      [["mois", "département", "entrees", "normale", "ratio"]]),
                              titre="Les pics départementaux"), lg=6, className="mb-3"),
                dbc.Col(carte(tableau(pics_s.assign(ratio=pics_s["ratio"].round(1), normale=pics_s["normale"].round(0))
                                      [["mois", "secteur", "entrees", "normale", "ratio"]].head(10)),
                              titre="Les pics sectoriels (10 plus forts)"), lg=6, className="mb-3"),
            ]),
        ),
    ])
