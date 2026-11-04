"""Réseaux (axes 7, 8, 9) — page de Luka.

Données : notebooks/axes/graphe_secteurs.ipynb, graphe_departements.ipynb, entreprises_liees.ipynb
-> data/dashboard/graphe_*.parquet, entreprises_liees_*.parquet, departements.geojson
"""
import json
from functools import lru_cache

import dash
import dash_bootstrap_components as dbc
import networkx as nx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, callback, dcc, html

from design import (ACCENT, AUTRE, ENCRE, SERIES, badge, boutons_segmentes, carte, chiffre_cle, couleur_groupe,
                    encadre, encart_perimetre, entete, figure_reseau, filtre, filtres, graphe, gris_sauf, methode, nombre,
                    pour_mille, question, tableau, zoom)
from donnees import DASHBOARD, NAF_SECTIONS, TOUS, est_filtre, libelle_perimetre, lire

dash.register_page(__name__, path="/secteurs", name="Secteurs et territoires", order=4, section="Analyses")


@lru_cache(maxsize=None)
def geojson():
    return json.load(open(DASHBOARD / "departements.geojson", encoding="utf-8"))


def figure_evolution(nom_fichier):
    e = lire(nom_fichier)
    dates = pd.to_datetime(e.index)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=100 * e["Ensemble"], name="Ensemble", line=dict(color=AUTRE, width=2, dash="dot"),
                             hovertemplate="Ensemble : %{y:.0f} %<extra></extra>"))
    for col in [c for c in e.columns if c.startswith("Communauté")]:
        i = int(col.split()[-1])
        fig.add_trace(go.Scatter(x=dates, y=100 * e[col], name=col, line=dict(color=couleur_groupe(i)),
                                 hovertemplate=f"{col} : %{{y:.0f}} %<extra></extra>"))
    fig.add_vrect(x0="2020-03-01", x1="2021-12-31", fillcolor=ENCRE["discrete"], opacity=0.08, line_width=0,
                  annotation_text="Covid", annotation_position="top left",
                  annotation_font=dict(size=11, color=ENCRE["discrete"]))
    fig.add_hline(y=0, line=dict(color="#c3c2b7", width=1))
    fig.update_layout(yaxis=dict(title="évolution sur 12 mois (%)"), hovermode="x unified", margin=dict(t=40))
    return fig


def tableau_communautes(nom_fichier):
    c = lire(nom_fichier).copy()
    c["creux Covid (%)"] = c["creux Covid (%)"].round(0).astype(int)
    c["pic du rattrapage (%)"] = c["pic du rattrapage (%)"].round(0).astype(int)
    c = c.rename(columns={"communauté": "n°", "creux Covid (%)": "creux Covid", "pic du rattrapage (%)": "pic",
                          "date du pic": "date du pic", "secteur principal": "le plus grand", "plus grand": "le plus grand"})
    c["creux Covid"] = c["creux Covid"].astype(str) + "\u202f%"
    c["pic"] = "+" + c["pic"].astype(str) + "\u202f%"
    return tableau(c)


# --------------------------------------------------------------------------- onglet secteurs (axe 8)
def onglet_secteurs():
    n = lire("graphe_secteurs_noeuds")
    return html.Div([
        dbc.Row([
            dbc.Col(chiffre_cle("Secteurs dans le graphe", str(len(n)), "sur 62 secteurs avec au moins 500 défaillances"),
                    md=6, xl=3, className="mb-4"),
            dbc.Col(chiffre_cle("Liens", nombre(len(lire("graphe_secteurs_aretes"))), "similarité de Spearman ≥ 0,60"),
                    md=6, xl=3, className="mb-4"),
            dbc.Col(chiffre_cle("Communautés (Louvain)", str(n["communauté"].nunique()), "modularité 0,16 : structure peu marquée"),
                    md=6, xl=3, className="mb-4"),
            dbc.Col(chiffre_cle("Small world", "σ = 1,84", "clustering 0,58 contre 0,28 au hasard"), md=6, xl=3,
                    className="mb-4"),
        ]),
        filtres(filtre("Disposition", boutons_segmentes("re-s-vue", [
            {"label": "Graphe", "value": "graphe"}, {"label": "Carte node2vec", "value": "carte"}], "graphe"))),
        carte(graphe("re-s-reseau", hauteur=560),
              titre="Les secteurs qui « souffrent ensemble »",
              description="Deux secteurs sont reliés si leurs défaillances évoluent pareil (évolution sur 12 mois, "
                          "corrélation de Spearman ≥ 0,60). Couleur = communauté de Louvain, taille = PageRank. "
                          "« Carte node2vec » : les secteurs placés par node2vec puis t-SNE.",
              pied="Seuil choisi par la méthode du coude ; nombre de communautés par la règle « meilleure modularité "
                   "moyenne sur 50 graines, puis nombre le plus fréquent ».", className="mb-4"),
        dbc.Row([
            dbc.Col(carte(graphe("re-s-evolution", figure_evolution("graphe_secteurs_evolution"), hauteur=380),
                          titre="Comment chaque communauté a vécu les crises",
                          description="Évolution moyenne des défaillances sur 12 mois glissants."), lg=7, className="mb-4"),
            dbc.Col(carte(tableau_communautes("graphe_secteurs_communautes"), titre="Les communautés"), lg=5,
                    className="mb-4"),
        ]),
        encadre("sans les années 2020-2024, les secteurs ne se ressemblent presque plus (similarité médiane 0,10 au lieu "
                "de 0,43). Le graphe décrit surtout comment ils ont vécu le Covid puis le rattrapage : toutes les "
                "communautés chutent d'environ 40 %, et c'est au rebond qu'elles se distinguent.", titre="À retenir :"),
    ])


@callback(Output("re-s-reseau", "figure"), Input("re-s-vue", "value"))
def maj_secteurs(vue):
    n = lire("graphe_secteurs_noeuds").set_index("division")
    n["survol"] = [f"<b>{r['secteur']}</b><br>communauté {r['communauté']} · {r['degré']} voisins<br>"
                   f"{nombre(r['défaillances'])} défaillances (2008-2026)" for _, r in n.iterrows()]
    n["etiquette"] = [s[:24] if p >= n["pagerank"].nlargest(8).min() else "" for s, p in zip(n["secteur"], n["pagerank"])]
    x, y = ("x_graphe", "y_graphe") if vue == "graphe" else ("x_carte", "y_carte")
    aretes = lire("graphe_secteurs_aretes") if vue == "graphe" else lire("graphe_secteurs_aretes").iloc[0:0]
    return figure_reseau(n, aretes, x, y, "communauté", "pagerank", "survol", texte="etiquette")


# --------------------------------------------------------------------------- onglet départements (axe 9)
def onglet_departements():
    n = lire("graphe_departements_noeuds")
    return html.Div([
        dbc.Row([
            dbc.Col(chiffre_cle("Départements dans le graphe", str(len(n)), "sur 100 avec au moins 500 défaillances"),
                    md=6, xl=3, className="mb-4"),
            dbc.Col(chiffre_cle("Liens", nombre(len(lire("graphe_departements_aretes"))), "similarité de Spearman ≥ 0,67"),
                    md=6, xl=3, className="mb-4"),
            dbc.Col(chiffre_cle("Communautés (Louvain)", str(n["communauté"].nunique()), "modularité 0,19 : structure peu marquée"),
                    md=6, xl=3, className="mb-4"),
            dbc.Col(chiffre_cle("Liens entre voisins", "8 %", "contre 5,2 % au hasard : la géographie joue peu"),
                    md=6, xl=3, className="mb-4"),
        ]),
        dbc.Row([
            dbc.Col(carte(graphe("re-d-carte", figure_carte_departements(), hauteur=560),
                          titre="Les communautés sur la carte",
                          description="Couleur = communauté de Louvain. Gris : département isolé ou non gardé.",
                          pied="Métropole uniquement. Outre-mer : Guadeloupe et Martinique dans des communautés, "
                               "Guyane et La Réunion isolées."), lg=6, className="mb-4"),
            dbc.Col(carte(graphe("re-d-reseau", figure_reseau_departements(), hauteur=560),
                          titre="Le graphe des départements",
                          description="Deux départements sont reliés si leurs défaillances évoluent pareil "
                                      "(Spearman ≥ 0,67). Taille = PageRank."), lg=6, className="mb-4"),
        ]),
        dbc.Row([
            dbc.Col(carte(graphe("re-d-evolution", figure_evolution("graphe_departements_evolution"), hauteur=380),
                          titre="Comment chaque communauté a vécu les crises"), lg=7, className="mb-4"),
            dbc.Col(carte(tableau_communautes("graphe_departements_communautes"), titre="Les communautés"), lg=5,
                    className="mb-4"),
        ]),
        encadre("les communautés de départements ne sont pas géographiques : chacune est éclatée en 9 à 12 morceaux "
                "sur la carte. Les cinq ont vécu le Covid de façon très proche et diffèrent surtout par le calendrier "
                "du rattrapage.", titre="À retenir :"),
    ])


def figure_carte_departements():
    n = lire("graphe_departements_noeuds")
    tous = pd.DataFrame({"departement": [f["properties"]["code"] for f in geojson()["features"]],
                         "nom": [f["properties"]["nom"] for f in geojson()["features"]]})
    d = tous.merge(n[["departement", "communauté", "degré"]], on="departement", how="left")
    d["groupe"] = d["communauté"].map(lambda c: f"Communauté {int(c)}" if pd.notna(c) else "isolé")
    couleurs = {f"Communauté {i}": couleur_groupe(i) for i in range(1, 9)} | {"isolé": "#e9e8e3"}
    fig = px.choropleth(d, geojson=geojson(), locations="departement", featureidkey="properties.code", color="groupe",
                        color_discrete_map=couleurs, hover_name="nom",
                        category_orders={"groupe": sorted(d["groupe"].unique(), key=lambda g: (g == "isolé", g))},
                        hover_data={"departement": False, "groupe": True, "degré": True})
    fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator", bgcolor="rgba(0,0,0,0)")
    fig.update_traces(marker_line_color="#fcfcfb", marker_line_width=0.6)
    fig.update_layout(margin=dict(l=0, r=0, t=40, b=0), legend_title_text="")
    return fig


def figure_reseau_departements():
    n = lire("graphe_departements_noeuds").set_index("departement")
    n["survol"] = [f"<b>{r['département']}</b><br>communauté {r['communauté']} · {r['degré']} voisins<br>"
                   f"{nombre(r['défaillances'])} défaillances" for _, r in n.iterrows()]
    return figure_reseau(n, lire("graphe_departements_aretes"), "x_graphe", "y_graphe", "communauté", "pagerank",
                         "survol", taille_max=26)


# --------------------------------------------------------------------------- onglet entreprises liées (axe 7)
@lru_cache(maxsize=None)
def stats_liees():
    n = lire("entreprises_liees_noeuds")
    a = lire("entreprises_liees_aretes")
    dep = n.set_index("siren")["departement"].astype("string")
    sect = n.set_index("siren")["secteur"].astype("string")
    meme_dep = (dep.reindex(a["source"]).reset_index(drop=True) == dep.reindex(a["cible"]).reset_index(drop=True)).fillna(False)
    meme_sect = (sect.reindex(a["source"]).reset_index(drop=True) == sect.reindex(a["cible"]).reset_index(drop=True)).fillna(False)
    tailles = n.dropna(subset=["composante"]).groupby("composante").size()
    return {"entreprises": int(n["composante"].notna().sum()), "liens": len(a), "composantes": int(tailles.size),
            "meme_dep": float(meme_dep.mean()), "meme_sect": float(meme_sect.mean()), "tailles": tailles}


def onglet_liees():
    s = stats_liees()
    t = s["tailles"].clip(upper=10).value_counts().sort_index()
    fig_t = go.Figure(go.Bar(x=[str(i) if i < 10 else "10 et +" for i in t.index], y=t.values, marker_color=SERIES[0],
                             hovertemplate="%{x} entreprises : %{y} groupes<extra></extra>"))
    fig_t.update_layout(xaxis=dict(title="taille du groupe (entreprises)", type="category"),
                        yaxis=dict(title="nombre de groupes"), margin=dict(t=16))
    secteurs = (lire("entreprises_liees_noeuds")["secteur"].value_counts(normalize=True).head(8) * 100).round(1)
    fig_s = go.Figure(go.Bar(x=secteurs.values[::-1], y=secteurs.index[::-1], orientation="h", marker_color=SERIES[0],
                             hovertemplate="%{y} : %{x:.1f} %<extra></extra>"))
    fig_s.update_layout(xaxis=dict(title="% des entreprises liées"), margin=dict(t=16, l=8))
    return html.Div([
        dbc.Row([
            dbc.Col(chiffre_cle("Entreprises liées", nombre(s["entreprises"]), "citées dans une même annonce qu'une autre"),
                    md=6, xl=3, className="mb-4"),
            dbc.Col(chiffre_cle("Groupes (composantes)", nombre(s["composantes"]), "presque tous fermés (cliques)"),
                    md=6, xl=3, className="mb-4"),
            dbc.Col(chiffre_cle("Même département", f"{100 * s['meme_dep']:.0f} %", "des paires liées, contre 2 % au hasard"),
                    md=6, xl=3, className="mb-4"),
            dbc.Col(chiffre_cle("Défaillances à moins d'un an", "76 %", "quand les deux entreprises défaillent (10 % au hasard)"),
                    md=6, xl=3, className="mb-4"),
        ]),
        dbc.Row([
            dbc.Col(carte(graphe("re-l-tailles", fig_t, hauteur=340), titre="La taille des groupes",
                          description="Un groupe = un morceau du graphe (une composante connexe).",
                          pied="L'unique annonce de plus de 60 entreprises (351) est écartée : c'est une liste groupée."),
                    lg=6, className="mb-4"),
            dbc.Col(carte(graphe("re-l-secteurs", fig_s, hauteur=340), titre="Les secteurs des entreprises liées",
                          description="L'immobilier pèse 26,5 % des entreprises liées, contre 3,5 % de l'ensemble des "
                                      "défaillantes (beaucoup de SCI)."), lg=6, className="mb-4"),
        ]),
        carte(graphe("re-l-groupe", figure_groupe(), hauteur=480),
              titre="Le plus grand groupe qui n'est pas une clique",
              description="36 entreprises reliées à travers plusieurs annonces (presque toutes dans les Alpes-Maritimes). "
                          "Couleur = communauté de Louvain, taille = nombre de liens.", className="mb-4"),
        encadre("le réseau est une juxtaposition de petits groupes fermés (3 128 morceaux sur 3 159 sont des cliques), "
                "très locaux. Quand deux entreprises liées défaillent toutes les deux, c'est souvent le même jour "
                "(jugées ensemble), sinon à quelques mois d'écart : un signe de contagion dans les groupes.",
                titre="À retenir :"),
    ])


@lru_cache(maxsize=None)
def figure_groupe():
    n = lire("entreprises_liees_noeuds")
    groupe = n[n["communaute_plus_grande"].notna()].set_index("siren")
    a = lire("entreprises_liees_aretes")
    a = a[a["source"].isin(groupe.index) & a["cible"].isin(groupe.index)]
    G = nx.from_pandas_edgelist(a, "source", "cible")
    pos = nx.spring_layout(G, seed=0, k=0.3)
    groupe = groupe.loc[list(G)]
    groupe["x"] = [pos[s][0] for s in groupe.index]
    groupe["y"] = [pos[s][1] for s in groupe.index]
    groupe["survol"] = [f"SIREN {s}<br>{r['secteur'] if pd.notna(r['secteur']) else 'secteur inconnu'}<br>"
                        f"forme juridique {r['categorie_juridique']} · département {r['departement']}<br>{r['degre']:.0f} liens"
                        for s, r in groupe.iterrows()]
    return figure_reseau(groupe, a, "x", "y", "communaute_plus_grande", "degre", "survol", taille_max=22)


# --------------------------------------------------------------------------- typologie (axe 11)
NOMS_SECT = {1: "commerce, construction, services", 2: "industrie et services techniques",
             3: "peu de défaillances", 4: "rattrapage explosif"}
NOMS_DEP = {1: "plus protégés pendant le Covid", 2: "moins protégés pendant le Covid", 3: "grandes agglomérations et Alsace",
            4: "outre-mer et Corse"}
INDIC = ["taux 2017-2019 (‰)", "part LJ directe", "effet Covid", "rattrapage", "part de jeunes"]


def figure_fragiles():
    t = lire("typologie_secteurs").sort_values("taux 2017-2019 (‰)")
    t = pd.concat([t.head(5), t.tail(10)])
    fig = go.Figure(go.Bar(x=t["taux 2017-2019 (‰)"], y=t["secteur"].astype(str), orientation="h",
                           marker_color=gris_sauf(len(t), [len(t) - 1, len(t) - 2, len(t) - 3], couleur=SERIES[1]),
                           text=[f"{v:.1f} ‰".replace(".", ",") for v in t["taux 2017-2019 (‰)"]], textposition="outside",
                           cliponaxis=False, textfont=dict(color=ENCRE["secondaire"]),
                           hovertemplate="%{y} : %{x:.1f} défaillances pour 1 000 entreprises par an<extra></extra>"))
    fig.add_hline(y=4.5, line=dict(color=ENCRE["discrete"], width=1, dash="dot"))
    fig.update_layout(xaxis=dict(title="défaillances par an pour 1 000 entreprises actives (2017-2019)", range=[0, 23]),
                      yaxis=dict(showgrid=False), margin=dict(t=16, r=40))
    return fig


def taux_2017_2019(par):
    """Taux annuel moyen 2017-2019 (‰) pour chaque couple (région, section) — « Total » compris."""
    t = lire("taux")
    t = t[t["annee"].astype(str).isin(["2017", "2018", "2019"]) & (t["cj_famille"] == "Total") & (t["tranche_age"] == "Total")]
    g = t.groupby([t["region"].astype(str), t["naf_section"].astype(str)])[["entreprises_defaillantes", "nb_actives"]].sum()
    g["taux"] = 1000 * g["entreprises_defaillantes"] / g["nb_actives"]
    return g


def figure_fragiles_perimetre(secteur, region):
    """Avec un filtre : les secteurs de la région choisie, ou les régions du secteur choisi, comparés à la France."""
    g = taux_2017_2019(None)
    par_secteur = region not in (None, TOUS)
    if (par_secteur and region not in g.index.get_level_values(0)) or \
            (not par_secteur and secteur not in g.index.get_level_values(1)):
        g = g.iloc[0:0]
    if g.empty:
        reg, fr, noms, titre = g, pd.Series(dtype=float), [], ""
    elif par_secteur:   # une région : ses secteurs, chacun comparé au même secteur en France
        reg = g.loc[region].drop(index=["Total", "non renseigné"], errors="ignore")
        reg = reg[reg["entreprises_defaillantes"] >= 30].sort_values("taux")
        fr = g.loc["Total"]["taux"].reindex(reg.index)
        noms = [NAF_SECTIONS.get(c, c) for c in reg.index]
        titre = f"Secteurs en {region}"
    else:             # un secteur : ses régions, comparées au secteur en France
        reg = g.xs(secteur, level=1).drop(index=["Total", "non renseigné", "Saint-Pierre-et-Miquelon"], errors="ignore")
        reg = reg[reg["entreprises_defaillantes"] >= 30].sort_values("taux")
        fr = pd.Series(g.loc[("Total", secteur), "taux"], index=reg.index)
        noms = list(reg.index)
        titre = NAF_SECTIONS.get(secteur, secteur)
    if reg.empty:
        fig = go.Figure()
        fig.add_annotation(text="Trop peu de défaillances dans ce périmètre (moins de 30 par secteur sur 2017-2019).",
                           showarrow=False, font=dict(size=13, color=ENCRE["secondaire"]), x=0.5, y=0.5,
                           xref="paper", yref="paper")
        fig.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False))
        return fig
    if par_secteur and secteur in reg.index:
        haut = [list(reg.index).index(secteur)]
    else:
        haut = list(range(max(len(reg) - 3, 0), len(reg)))
    fig = go.Figure(go.Bar(x=reg["taux"], y=noms, orientation="h", name=titre,
                           marker_color=gris_sauf(len(reg), haut, couleur=SERIES[1]),
                           text=[f"{v:.1f} ‰".replace(".", ",") for v in reg["taux"]], textposition="outside",
                           cliponaxis=False, textfont=dict(color=ENCRE["secondaire"]),
                           hovertemplate="%{y} : %{x:.1f} ‰ par an<extra></extra>"))
    fig.add_trace(go.Scatter(x=fr.values, y=noms, mode="markers", name="France (même secteur)",
                             marker=dict(symbol="line-ns", size=16, line=dict(width=2.5, color=ENCRE["secondaire"])),
                             hovertemplate="France : %{x:.1f} ‰<extra></extra>"))
    fig.update_layout(xaxis=dict(title="défaillances par an pour 1 000 entreprises actives (2017-2019)",
                                 range=[0, 1.2 * max(reg["taux"].max(), fr.max())]),
                      yaxis=dict(showgrid=False), margin=dict(t=40, r=40), showlegend=True,
                      legend=dict(orientation="h", y=1.08, x=0))
    return fig


@callback(Output("se-fragiles", "figure"), Output("se-zoom-2", "children"), Output("se-fragiles-titre", "children"),
          Input("filtre-secteur", "value"), Input("filtre-region", "value"))
def maj_fragiles(secteur, region):
    if not est_filtre(secteur, region):
        return figure_fragiles(), None, "Taux de défaillance par secteur (les 10 plus élevés et les 5 plus bas)"
    g = taux_2017_2019(None)
    lib = libelle_perimetre(secteur, region)
    r = region if region not in (None, TOUS) else "Total"
    sct = secteur if secteur not in (None, TOUS) else "Total"
    v = g["taux"].get((r, sct), float("nan"))
    fr = g.loc[("Total", sct), "taux"] if ("Total", sct) in g.index else float("nan")
    texte = [html.B(pour_mille(v)), " de défaillances par an avant le Covid (2017-2019), contre ", pour_mille(fr),
             " pour " + ("ce secteur en France." if sct != "Total" else "la France.")]
    if r != "Total":
        rang = g.loc[r].drop(index=["Total", "non renseigné"], errors="ignore")
        rang = rang[rang["entreprises_defaillantes"] >= 30]["taux"].sort_values(ascending=False)
        if rang.empty:
            texte += [" Trop peu de défaillances par secteur dans la région pour les comparer."]
        elif sct in rang.index:
            texte += [f" C'est le {list(rang.index).index(sct) + 1}e secteur le plus fragile de la région sur {len(rang)}."]
        else:
            texte += [f" Le plus fragile de la région : {NAF_SECTIONS.get(rang.index[0], rang.index[0])} "
                      f"({pour_mille(rang.iloc[0])})."]
        titre = f"Taux de défaillance par secteur en {region}, comparé au même secteur en France"
    else:
        titre = f"Taux de défaillance de « {NAF_SECTIONS.get(sct, sct)} » par région, comparé à la France"
    note = "Ici, les secteurs sont les grandes sections NAF (21), pas les 88 divisions du graphique national."
    return figure_fragiles_perimetre(secteur, region), encart_perimetre(lib, *texte, prudence=None), [titre, html.Div(note, className="ds-card__description")]


def figure_zones():
    t = lire("typologie_departements")
    d = t.assign(zone=t["groupe"].map(lambda g: NOMS_DEP[g] if g == 3 else "autres départements"))
    fig = px.choropleth(d, geojson=geojson(), locations="departement", featureidkey="properties.code", color="zone",
                        color_discrete_map={NOMS_DEP[3]: ACCENT, "autres départements": "#d6d4cc"}, hover_name="nom",
                        hover_data={"departement": False, "zone": False, "part LJ directe": ":.0%"},
                        category_orders={"zone": [NOMS_DEP[3], "autres départements"]})
    fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator", bgcolor="rgba(0,0,0,0)")
    fig.update_traces(marker_line_color="#fcfcfb", marker_line_width=0.6)
    fig.update_layout(margin=dict(l=0, r=0, t=40, b=0), legend_title_text="")
    return fig


def figure_contagion():
    s = stats_liees()
    mesures = ["dans le même département", "défaillantes à moins d'un an d'écart"]
    liees = [100 * s["meme_dep"], 76.4]      # 76,4 % : notebooks/axes/entreprises_liees.ipynb, section 6
    hasard = [2.1, 10.5]                      # paires de défaillantes tirées au hasard (même notebook)
    fig = go.Figure([
        go.Bar(name="entreprises liées", x=mesures, y=liees, marker_color=ACCENT,
               text=[f"{v:.0f} %" for v in liees], textposition="outside", cliponaxis=False),
        go.Bar(name="entreprises au hasard", x=mesures, y=hasard, marker_color="#d6d4cc",
               text=[f"{v:.0f} %" for v in hasard], textposition="outside", cliponaxis=False),
    ])
    fig.update_traces(textfont=dict(color=ENCRE["secondaire"]), hovertemplate="%{x} : %{y:.1f} %<extra>%{fullData.name}</extra>")
    fig.update_layout(barmode="group", yaxis=dict(title="% des paires", range=[0, 95]), margin=dict(t=40))
    return fig


def bloc_typologie():
    return html.Div([
        filtres(
            filtre("Regrouper", boutons_segmentes("ty-niveau", [{"label": "Secteurs", "value": "secteurs"},
                                                                {"label": "Départements", "value": "departements"}],
                                                  "secteurs")),
            filtre("Axe horizontal", dcc.Dropdown(INDIC, "taux 2017-2019 (‰)", id="ty-x", clearable=False)),
            filtre("Axe vertical", dcc.Dropdown(INDIC, "part LJ directe", id="ty-y", clearable=False)),
        ),
        carte(graphe("ty-nuage", hauteur=440), titre="Typologie : les groupes selon deux indicateurs",
              description="k-means sur 5 indicateurs (taux, liquidations directes, effet Covid, rattrapage, jeunes). "
                          "Taille = nombre de défaillances.", className="mb-3"),
        carte(html.Div(id="ty-tableau"), titre="Les groupes (médianes)", className="mb-3"),
    ])


@callback(Output("ty-nuage", "figure"), Output("ty-tableau", "children"),
          Input("ty-niveau", "value"), Input("ty-x", "value"), Input("ty-y", "value"))
def maj_typologie(niveau, x, y):
    t = lire(f"typologie_{niveau}").copy()
    noms = NOMS_SECT if niveau == "secteurs" else NOMS_DEP
    libelle = "secteur" if niveau == "secteurs" else "nom"
    fig = go.Figure()
    for g in sorted(t["groupe"].unique()):
        m = t["groupe"] == g
        fig.add_trace(go.Scatter(
            x=t.loc[m, x], y=t.loc[m, y], mode="markers", name=f"{g}. {noms[g]}",
            marker=dict(size=7 + 26 * (t.loc[m, "entrees_total"] / t["entrees_total"].max()) ** 0.5,
                        color=couleur_groupe(g), line=dict(width=1, color="#fcfcfb"), opacity=0.85),
            hovertext=t.loc[m, libelle], hovertemplate=f"<b>%{{hovertext}}</b><br>{x} : %{{x:.2f}}<br>{y} : %{{y:.2f}}<extra></extra>"))
    fig.update_layout(xaxis_title=x, yaxis_title=y, margin=dict(t=40))
    m = t.groupby("groupe")[INDIC].median()
    fr = lambda v, f: f.format(v).replace(".", ",")
    med = pd.DataFrame({
        "groupe": [f"{g}. {noms[g]}" for g in m.index], "nombre": t.groupby("groupe").size().to_numpy(),
        "taux 2017-2019": [fr(v, "{:.2f} ‰") for v in m["taux 2017-2019 (‰)"]],
        "liquidations directes": [fr(100 * v, "{:.0f} %") for v in m["part LJ directe"]],
        "effet Covid": [fr(v, "× {:.2f}") for v in m["effet Covid"]], "rattrapage": [fr(v, "× {:.2f}") for v in m["rattrapage"]],
        "jeunes entreprises": [fr(100 * v, "{:.0f} %") for v in m["part de jeunes"]],
    })
    return fig, tableau(med)


# --------------------------------------------------------------------------- page
def layout():
    return html.Div([
        entete("Secteurs et territoires",
               "Les secteurs et les départements font-ils faillite au même rythme ? Lesquels sont les plus fragiles ? "
               "Et la faillite se propage-t-elle d'une entreprise à l'autre ?",
               surtitre="Analyses", badges=[badge("Graphes, communautés, typologie", "accent"), badge("Responsable : Luka")]),
        question("Les secteurs font-ils faillite au même rythme ?",
                 [html.B("Avant 2020, non : "), "chaque secteur suivait son propre rythme. ",
                  html.B("C'est le Covid qui les a synchronisés"), " : tous ont chuté d'environ 40 %, puis rebondi. "
                  "Ils se distinguent surtout par ", html.B("la force du rebond"), ", de +54 % à +84 % selon les groupes."],
                 carte(graphe("se-evolution", figure_evolution("graphe_secteurs_evolution"), hauteur=360),
                       titre="Évolution des défaillances sur 12 mois, par groupe de secteurs",
                       pied="Sans les années 2020-2024, la similarité entre les courbes de deux secteurs tombe de 0,43 à "
                            "0,10 (Spearman, médiane). Groupes : communautés de Louvain du graphe des secteurs."),
                 numero=1),
        question("Quels secteurs sont les plus fragiles ?",
                 [html.B("La sécurité, la restauration et l'alimentaire"), " : 17 à 19 défaillances par an pour 1 000 "
                  "entreprises avant le Covid, ", html.B("plus de 20 fois plus"), " que l'immobilier ou la santé (moins de 1 ‰)."],
                 zoom("se-zoom-2"),
                 carte(html.Div(id="se-fragiles-titre", className="ds-card__title", style={"marginBottom": "8px"}),
                       graphe("se-fragiles", hauteur=480)),
                 numero=2),
        question("Y a-t-il des zones géographiques plus touchées ?",
                 [html.B("Pas de grandes zones : "), "les départements qui évoluent pareil sont dispersés sur la carte. "
                  "Mais ", html.B("les grandes agglomérations et l'Alsace"), " se distinguent : ",
                  html.B("83 % de leurs défaillances sont des liquidations directes"), ", contre 51 à 66 % ailleurs."],
                 carte(graphe("se-zones", figure_zones(), hauteur=480),
                       titre="Les départements à part : Paris et sa couronne, le Rhône, le Bas-Rhin et le Haut-Rhin",
                       pied="Groupe obtenu par la typologie (k-means sur 5 indicateurs). Survoler un département pour sa "
                            "part de liquidations directes."),
                 numero=3),
        question("La faillite se propage-t-elle d'une entreprise à l'autre ?",
                 [html.B("Dans les groupes d'entreprises, oui. "), "Quand deux entreprises liées font faillite, c'est ",
                  html.B("à moins d'un an d'écart dans 76 % des cas"), ", contre 10 % pour deux entreprises au hasard. "
                  "Ce sont surtout des ", html.B("groupes locaux"), " (même département dans 74 % des cas), avec "
                  "beaucoup de SCI et d'immobilier."],
                 carte(graphe("se-contagion", figure_contagion(), hauteur=320),
                       titre="Entreprises liées (citées dans une même annonce) contre entreprises prises au hasard",
                       pied="Une partie de l'effet est automatique : des entreprises liées sont souvent jugées le même jour."),
                 numero=4),
        methode(
            dbc.Tabs([
                dbc.Tab(onglet_secteurs(), label="Graphe des secteurs (axe 8)", tab_id="secteurs"),
                dbc.Tab(onglet_departements(), label="Graphe des départements (axe 9)", tab_id="departements"),
                dbc.Tab(onglet_liees(), label="Entreprises liées (axe 7)", tab_id="liees"),
                dbc.Tab(bloc_typologie(), label="Typologie (axe 11)", tab_id="typologie"),
            ], active_tab="secteurs", className="ds-tabs"),
        ),
    ])
