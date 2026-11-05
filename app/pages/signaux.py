"""Signaux financiers : profils (axe 10) et prédiction (axe 12) — page de Luka.

Données : notebooks/axes/profils_financiers.ipynb, prediction.ipynb -> data/dashboard/profils_*, prediction_*
"""
import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, callback, dcc, html

from design import (ACCENT, AUTRE, DIVERGENTE, ENCRE, SERIES, badge, boutons_segmentes, carte, couleur_groupe,
                    encart_perimetre, entete, filtre, filtres, graphe, gris_sauf, methode, nombre, pct, question,
                    tableau, zoom)
from donnees import TOUS, est_filtre, libelle_perimetre, lire, risque_profils

dash.register_page(__name__, path="/signaux", name="Signaux financiers", order=5, section="Analyses")

NOMS_PROFILS = {1: "rentables, payées comptant", 2: "installées et solides",
                3: "en perte, capitaux propres négatifs", 4: "en perte, mais encore solides"}


# --------------------------------------------------------------------------- onglet profils (axe 10)
def figure_risque(secteur=TOUS, region=TOUS):
    filtre_actif = est_filtre(secteur, region)
    r = risque_profils(secteur, region).sort_index(ascending=False)
    fr = risque_profils(TOUS, TOUS).sort_index(ascending=False)
    noms = [f"{p}. {NOMS_PROFILS[p]}".replace(", ", ",<br>") for p in r.index]
    fig = go.Figure(go.Bar(
        y=noms, x=r["taux"], orientation="h", name=libelle_perimetre(secteur, region),
        marker_color=[SERIES[1] if p == 3 else "#d6d4cc" for p in r.index],
        text=[("—" if v != v else f"{v:.1f} %".replace(".", ",")) for v in r["taux"]], textposition="outside",
        textfont=dict(color=ENCRE["secondaire"]), cliponaxis=False, customdata=r["exercices"],
        hovertemplate="%{y}<br>faillite dans les 36 mois : %{x:.2f} % (%{customdata:,.0f} comptes)<extra></extra>"))
    moyenne = 100 * r["faillites"].sum() / r["exercices"].sum() if r["exercices"].sum() else float("nan")
    if moyenne == moyenne:
        fig.add_vline(x=moyenne, line=dict(color=AUTRE, width=1, dash="dot"),
                      annotation_text=f"moyenne {moyenne:.1f} %".replace(".", ","), annotation_position="top",
                      annotation_font=dict(size=11, color=ENCRE["discrete"]))
    maxi = max(r["taux"].max() if r["taux"].notna().any() else 0, fr["taux"].max() if filtre_actif else 0)
    if filtre_actif:
        fig.add_trace(go.Scatter(x=fr["taux"], y=noms, mode="markers", name="France",
                                 marker=dict(symbol="line-ns", size=22, line=dict(width=3, color=ENCRE["secondaire"])),
                                 hovertemplate="France : %{x:.2f} %<extra></extra>"))
        fig.update_layout(showlegend=True, legend=dict(orientation="h", y=1.16, x=0))
    fig.update_layout(xaxis=dict(title="% d'exercices suivis d'une faillite", range=[0, 1.18 * maxi]),
                      yaxis=dict(showgrid=False), margin=dict(t=40, l=8, r=24))
    return fig


@callback(Output("pr-risque", "figure"), Output("pr-zoom-1", "children"),
          Input("filtre-secteur", "value"), Input("filtre-region", "value"))
def maj_risque(secteur, region):
    fig = figure_risque(secteur, region)
    if not est_filtre(secteur, region):
        return fig, None
    r = risque_profils(secteur, region)
    lib = libelle_perimetre(secteur, region)
    if r["exercices"].sum() == 0:
        return fig, encart_perimetre(lib, "Pas de comptes annuels publiés dans ce périmètre.")
    solide = r.loc[[1, 2], "taux"].min()   # le profil le plus sûr du périmètre (1 ou 2 selon les cas)
    rapport = r.at[3, "taux"] / solide if solide > 0 else float("nan")
    texte = ["Le profil « en perte, capitaux propres négatifs » fait faillite dans ", html.B(pct(r.at[3, "taux"], 1)),
             " des cas, contre ", pct(solide, 1), " pour le profil le plus sûr"]
    texte += ([" : ", html.B(f"{rapport:.0f} fois plus"), " (France : 5 fois)."] if rapport == rapport else ["."])
    prudence = (f"Seulement {nombre(r['faillites'].sum())} faillites suivies dans ce périmètre : les écarts entre "
                "profils sont fragiles." if r["faillites"].sum() < 100 else None)
    return fig, encart_perimetre(lib, *texte, prudence=prudence)


def figure_centres():
    c = lire("profils_centres").set_index("profil")
    fig = go.Figure(go.Heatmap(
        z=c.to_numpy(), x=list(c.columns), y=[f"{p}. {NOMS_PROFILS[p]}" for p in c.index],
        zmin=-2, zmax=2, colorscale=[[i / (len(DIVERGENTE) - 1), col] for i, col in enumerate(DIVERGENTE)],
        text=[[f"{v:+.1f}" for v in ligne] for ligne in c.to_numpy()], texttemplate="%{text}",
        textfont=dict(size=12), colorbar=dict(title="z-score", thickness=10),
        hovertemplate="%{y}<br>%{x} : %{z:+.2f} écart-type<extra></extra>", xgap=2, ygap=2))
    fig.update_layout(xaxis=dict(tickangle=-25, showgrid=False, side="top"), yaxis=dict(showgrid=False, autorange="reversed"),
                      margin=dict(t=70, l=8))
    return fig


def figure_choix_k():
    k = lire("profils_choix_k")
    fig = go.Figure(go.Scatter(x=k["k"], y=k["silhouette"], mode="lines+markers", line=dict(color=SERIES[0]),
                               hovertemplate="k = %{x} : silhouette %{y:.3f}<extra></extra>"))
    fig.add_vline(x=4, line=dict(color=AUTRE, width=1), annotation_text="k retenu", annotation_position="top right",
                  annotation_font=dict(size=11, color=ENCRE["discrete"]))
    fig.update_layout(xaxis=dict(title="nombre de groupes k", dtick=1), yaxis=dict(title="silhouette"), margin=dict(t=24))
    return fig


def figure_acp():
    v = lire("profils_acp_variance")
    fig = go.Figure(go.Bar(x=v["composante"], y=100 * v["variance"], marker_color=SERIES[0],
                           hovertemplate="%{x} : %{y:.1f} % de la variance<extra></extra>"))
    fig.add_trace(go.Scatter(x=v["composante"], y=100 * v["variance"].cumsum(), mode="lines+markers", name="cumulée",
                             line=dict(color=AUTRE), hovertemplate="cumulée : %{y:.0f} %<extra></extra>"))
    fig.update_layout(yaxis=dict(title="% de la variance"), showlegend=False, margin=dict(t=16))
    return fig


@callback(Output("pr-points", "figure"), Input("pr-proj", "value"), Input("pr-couleur", "value"))
def maj_points(proj, couleur):
    p = lire("profils_points")
    x, y = ("tsne_x", "tsne_y") if proj == "tsne" else ("pc1", "pc2")
    fig = go.Figure()
    if couleur == "profil":
        for k in sorted(p["profil"].unique()):
            m = p["profil"] == k
            fig.add_trace(go.Scattergl(x=p.loc[m, x], y=p.loc[m, y], mode="markers", name=f"{k}. {NOMS_PROFILS[k]}",
                                       marker=dict(size=5, color=couleur_groupe(k), opacity=0.7),
                                       hovertemplate=f"profil {k}<extra></extra>"))
    else:
        for val, nom, coul, taille in [(False, "pas de faillite", "#d6d4cc", 4), (True, "faillite dans les 36 mois", SERIES[1], 7)]:
            m = p["faillite_36_mois"] == val
            fig.add_trace(go.Scattergl(x=p.loc[m, x], y=p.loc[m, y], mode="markers", name=nom,
                                       marker=dict(size=taille, color=coul, opacity=0.8),
                                       hovertemplate=f"{nom}<extra></extra>"))
    fig.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False), margin=dict(t=40))
    return fig


# --------------------------------------------------------------------------- prédiction (axe 12)
NOMS_VARIABLES = {
    "ratio_de_liquidite": "liquidité", "naf_section": "secteur", "poids_bfr_exploitation_sur_ca_jours": "BFR (jours)",
    "autonomie_financiere": "autonomie financière", "taux_d_endettement": "endettement", "age_ans": "âge",
    "log_ca": "taille (chiffre d'affaires)", "resultat_courant_avant_impots_sur_ca": "résultat courant / CA",
    "caf_sur_ca": "CAF / CA", "capacite_de_remboursement": "capacité de remboursement",
    "couverture_des_interets": "couverture des intérêts", "marge_ebe": "marge d'EBE",
}


def figure_signaux():
    imp = lire("prediction_importance").head(8).iloc[::-1]
    noms = [NOMS_VARIABLES.get(v, v) for v in imp["variable"]]
    fig = go.Figure(go.Bar(x=imp["importance"], y=noms, orientation="h",
                           marker_color=gris_sauf(len(imp), [len(imp) - 1], couleur=ACCENT),
                           hovertemplate="%{y} : l'AUC baisse de %{x:.3f} quand on la mélange<extra></extra>"))
    fig.update_layout(xaxis=dict(title="importance dans le modèle (baisse de l'AUC quand on mélange la variable)"),
                      yaxis=dict(showgrid=False), margin=dict(t=16))
    return fig


def figure_detection():
    s = lire("prediction_scores").set_index("modèle")
    ordre = ["hasard", "régression logistique", "arbre de décision (profondeur 4)", "gradient boosting"]
    v = 100 * s.loc[ordre, "rappel (top 10 %)"]
    fig = go.Figure(go.Bar(x=v.values, y=["au hasard", "régression logistique", "arbre de décision", "gradient boosting"],
                           orientation="h", marker_color=gris_sauf(4, [3], couleur=ACCENT),
                           text=[f"{x:.0f} %" for x in v.values], textposition="outside", cliponaxis=False,
                           textfont=dict(color=ENCRE["secondaire"]),
                           hovertemplate="%{y} : %{x:.0f} % des faillites repérées<extra></extra>"))
    fig.update_layout(xaxis=dict(title="% des faillites repérées en surveillant 10 % des entreprises", range=[0, 60]),
                      yaxis=dict(showgrid=False), margin=dict(t=16, r=30))
    return fig


def figure_roc():
    r = lire("prediction_roc")
    sc = lire("prediction_scores").set_index("modèle")
    fig = go.Figure()
    for modele, couleur in zip(r["modele"].unique(), SERIES):
        m = r["modele"] == modele
        fig.add_trace(go.Scatter(x=r.loc[m, "faux_positifs"], y=r.loc[m, "rappel"], mode="lines", line=dict(color=couleur),
                                 name=f"{modele} (AUC {sc.loc[modele, 'AUC']:.2f})".replace(".", ",")))
    fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="hasard", line=dict(color=AUTRE, dash="dot")))
    fig.update_layout(xaxis=dict(title="faux positifs", tickformat=".0%"), yaxis=dict(title="faillites repérées",
                      tickformat=".0%"), margin=dict(t=40))
    return fig


# --------------------------------------------------------------------------- page
def layout():
    r = lire("profils_resume").set_index("profil")
    colonnes = ["taux_faillite", "liquidité", "autonomie fin.", "endettement", "marge EBE", "résultat courant / CA",
                "crédit clients (j)"]
    medianes = r[colonnes].astype("float64").round(1).map(lambda v: f"{v:g}".replace(".", ","))
    medianes = medianes.rename(columns={"taux_faillite": "faillite", "autonomie fin.": "autonomie",
                                        "résultat courant / CA": "résultat / CA", "crédit clients (j)": "clients (j)"})
    medianes.insert(0, "exercices", r["exercices"].map(nombre))
    medianes.insert(0, "profil", [f"{p}. {NOMS_PROFILS[p]}" for p in medianes.index])
    scores = lire("prediction_scores").copy()   # copie : ne pas modifier le tableau en cache
    for c in scores.columns[1:]:
        scores[c] = scores[c].map(lambda v: f"{v:.3f}".replace(".", ","))
    return html.Div([
        entete("Signaux financiers",
               "Les comptes d'une entreprise permettent-ils de voir venir sa faillite ? On regarde les ratios financiers "
               "de 2,9 millions de comptes annuels, et ce qui leur arrive dans les 3 années suivantes.",
               surtitre="Analyses", badges=[badge("ACP, k-means, t-SNE, classification", "accent"), badge("Responsable : Luka")]),
        question("Peut-on voir venir une faillite dans les comptes ?",
                 [html.B("Oui, en partie. "), "Sans même savoir qui a fait faillite, on retrouve 4 profils d'entreprises. "
                  "Le profil ", html.B("« en perte, capitaux propres négatifs »"), " fait ",
                  html.B("5 fois plus faillite"), " que le plus solide (6,8 % contre 1,3 % dans les 3 ans)."],
                 zoom("pr-zoom-1"),
                 carte(graphe("pr-risque", hauteur=340),
                       titre="Part des comptes suivis d'une faillite dans les 36 mois, par profil financier"),
                 numero=1),
        question("Quel signal regarder en premier ?",
                 [html.B("La trésorerie (liquidité)"), ", loin devant le reste. Viennent ensuite le secteur, le besoin "
                  "en fonds de roulement, les capitaux propres et l'endettement. ", html.B("La rentabilité compte beaucoup "
                  "moins"), " : une entreprise peut perdre de l'argent un temps, pas manquer de trésorerie."],
                 carte(graphe("pr-signaux", figure_signaux(), hauteur=320),
                       titre="Les 8 informations les plus utiles pour prévoir une faillite"),
                 numero=2),
        question("Un modèle peut-il prévoir les faillites ? (bonus)",
                 [html.B("En partie. "), "En surveillant les 10 % d'entreprises les plus à risque selon le modèle, on "
                  "repère ", html.B("près de la moitié (48 %) des faillites"), " des 3 années suivantes, contre 10 % au "
                  "hasard. Mais ", html.B("9 alertes sur 10 sont fausses"), " : la faillite reste rare (2 % des comptes)."],
                 carte(graphe("pr-detection", figure_detection(), hauteur=260),
                       titre="Faillites repérées en surveillant 10 % des entreprises",
                       pied="Modèles appris sur les comptes 2016-2020, testés sur 2021-2023 (400 000 comptes)."),
                 numero=3),
        methode(
            dbc.Tabs([
                dbc.Tab(html.Div([
                    carte(tableau(medianes), titre="Les profils en chiffres (médianes)",
                          pied="Faillite et ratios en %, délai clients en jours. Un endettement négatif veut dire des "
                               "capitaux propres négatifs.", className="mb-3"),
                    carte(graphe("pr-centres", figure_centres(), hauteur=330), titre="Ce qui distingue les profils (z-score)",
                          className="mb-3"),
                    filtres(
                        filtre("Projection", boutons_segmentes("pr-proj", [{"label": "t-SNE", "value": "tsne"},
                                                                           {"label": "ACP", "value": "acp"}], "tsne")),
                        filtre("Couleur", boutons_segmentes("pr-couleur", [{"label": "Profil", "value": "profil"},
                                                                           {"label": "Faillite à 36 mois", "value": "faillite"}],
                                                            "profil")),
                    ),
                    carte(graphe("pr-points", hauteur=480), titre="5 000 entreprises sur une carte", className="mb-3"),
                    dbc.Row([
                        dbc.Col(carte(graphe("pr-k", figure_choix_k(), hauteur=280), titre="Choix du nombre de groupes",
                                      description="Silhouette maximale à k = 2, coude à k = 5 : pas de groupes nets, k = 4 "
                                                  "retenu car il sépare bien le risque."), lg=6),
                        dbc.Col(carte(graphe("pr-acp", figure_acp(), hauteur=280), titre="ACP : variance expliquée",
                                      description="Il faut 6 composantes pour dépasser 70 % : les ratios se résument mal."), lg=6),
                    ]),
                ]), label="Profils financiers (axe 10)", tab_id="profils"),
                dbc.Tab(html.Div([
                    carte(graphe("pd-roc", figure_roc(), hauteur=380), titre="Courbes ROC", className="mb-3"),
                    carte(tableau(scores), titre="Les trois modèles",
                          pied="Classes pondérées pendant l'apprentissage. Variables : 13 ratios, chiffre d'affaires, âge, "
                               "secteur, forme juridique."),
                ]), label="Prédiction (axe 12)", tab_id="prediction"),
            ], active_tab="profils", className="ds-tabs"),
        ),
    ])
