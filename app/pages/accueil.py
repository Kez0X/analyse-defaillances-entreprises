"""Page d'accueil : le fil rouge (gel puis rattrapage incomplet), « Et pour vous ? » et ce qu'il faut retenir."""
import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, callback, dcc, html

from design import (ACCENT, ENCRE, badge, carte, chiffre_cle, encart_perimetre, entete, graphe, methode, nombre, pct,
                    pour_mille, reponse_cle)
from donnees import (TOUS, bilan_rattrapage, est_filtre, issues_redressements, libelle_perimetre,
                     part_liquidation_directe, risque_profils, serie_perimetre, taux_perimetre)

dash.register_page(__name__, path="/", name="Accueil", order=0, section="Exploration")

RETENIR = [
    ([html.B("Un seul vrai choc depuis 2008 : le Covid."), " De 2020 à 2022, deux fois moins de défaillances que "
      "d'habitude, soit environ 68 000 « manquantes »."], "/evenements", "Événements de masse"),
    ([html.B("2024-2025 : un record en nombre, pas en taux."), " Plus de 60 000 entreprises par an, mais 3,8 ‰ des "
      "entreprises contre 6,3 ‰ en 2009."], "/evenements", "Événements de masse"),
    ([html.B("Une procédure se finit presque toujours mal."), " 2 entreprises sur 3 sont liquidées directement, et "
      "7 redressements sur 10 finissent en liquidation."], "/parcours", "Parcours des procédures"),
    ([html.B("Le Covid a réduit les chances de s'en sortir."), " Redressements sauvés : environ 22 % avant, "
      "17 % depuis 2021."], "/parcours", "Parcours des procédures"),
    ([html.B("Sécurité, restauration, alimentaire : les plus fragiles."), " 17 à 19 défaillances pour 1 000 "
      "entreprises par an, plus de 20 fois plus que l'immobilier."], "/secteurs", "Secteurs et territoires"),
    ([html.B("La faillite se propage dans les groupes."), " Deux entreprises liées défaillent à moins d'un an "
      "d'écart dans 76 % des cas (10 % au hasard)."], "/secteurs", "Secteurs et territoires"),
    ([html.B("Les comptes donnent l'alerte."), " Le profil « en perte, capitaux propres négatifs » fait 5 fois plus "
      "faillite ; la trésorerie est le premier signal."], "/signaux", "Signaux financiers"),
    ([html.B("Les tribunaux jugent de plus en plus en masse."), " Plus de 20 journées par an à 50 défaillances "
      "ou plus dans un même tribunal depuis 2024."], "/evenements", "Événements de masse"),
]


def figure_solde(secteur, region):
    """Le fil rouge : l'écart cumulé à la normale depuis janvier 2020 (négatif = défaillances « manquantes »)."""
    d = serie_perimetre(secteur, region).loc["2020-01":]
    dates = pd.to_datetime(d.index)
    fig = go.Figure()
    fig.add_vrect(x0="2020-01-01", x1="2022-08-31", fillcolor=ACCENT, opacity=0.08, line_width=0,
                  annotation_text="Covid : le gel", annotation_position="top left",
                  annotation_font=dict(size=12, color=ENCRE["primaire"]))
    fig.add_trace(go.Scatter(x=dates, y=d["solde"], mode="lines", line=dict(color=ACCENT, width=2.5), fill="tozeroy",
                             fillcolor="rgba(42,120,214,0.12)", customdata=d[["entrees", "reference"]],
                             hovertemplate="%{x|%B %Y}<br>solde : %{y:,.0f}<br>ce mois-ci : %{customdata[0]:,.0f} "
                                           "défaillances (normale %{customdata[1]:,.0f})<extra></extra>"))
    fig.add_hline(y=0, line=dict(color=ENCRE["discrete"], width=1))
    bas = d["solde"].idxmin()
    fin = d.index[-1]
    for x, texte, ax, ay in [(bas, f"au plus bas : {nombre(d.at[bas, 'solde'])}", 0, 34),
                             (fin, f"octobre 2026 : {nombre(d.at[fin, 'solde'])}", -40, -34)]:
        if x == fin and x == bas and texte.startswith("au plus bas"):
            continue
        fig.add_annotation(x=pd.to_datetime(x), y=d.at[x, "solde"], text=texte, showarrow=True, arrowhead=0, ax=ax, ay=ay,
                           font=dict(size=11, color=ENCRE["primaire"]))
    fig.update_layout(yaxis=dict(title="écart cumulé à la normale"),
                      showlegend=False, margin=dict(t=32, r=24), separators=", ")
    return fig


def texte_fil_rouge(b, perimetre):
    """La phrase du fil rouge, selon ce qui s'est passé dans le périmètre."""
    m, apres = b["manquantes"], b["depuis"]
    if m < 20:
        return [html.B(f"{perimetre} : pas de gel visible pendant le Covid. "),
                "Les défaillances y sont restées proches de la normale de 2020 à 2022."]
    debut = [html.B(nombre(m)), " défaillances « manquantes » pendant le Covid (janvier 2020 - août 2022). "]
    if apres <= 0:
        suite = [html.B("Le rattrapage n'a pas commencé"), " : depuis septembre 2022, il y en a encore eu ",
                 html.B(nombre(-apres)), " de moins que la normale."]
    elif apres < m:
        suite = ["Depuis, ", html.B(f"seulement {nombre(apres)} ont été rattrapées ({pct(100 * apres / m)})"),
                 f" : il en manque encore {nombre(-b['solde'])}."]
    else:
        suite = [html.B("Le rattrapage est fini, et dépassé"), f" : depuis septembre 2022, {nombre(apres)} défaillances "
                 "de plus que la normale, soit plus que celles qui manquaient."]
    return debut + suite


def tuiles_pour_vous(secteur, region):
    """« Et pour vous ? » : 4 repères pour un chef d'entreprise, un banquier, un expert-comptable du périmètre."""
    filtre_actif = est_filtre(secteur, region)
    fr = lambda f, *a: f(TOUS, TOUS, *a)
    t, t_fr = taux_perimetre(secteur, region), fr(taux_perimetre)
    ind, ind_fr = bilan_rattrapage(secteur, region)["indice_recent"], fr(bilan_rattrapage)["indice_recent"]
    lj, n_lj = part_liquidation_directe(secteur, region)
    lj_fr, _ = fr(part_liquidation_directe)
    iss, n_rj = issues_redressements(secteur, region)
    iss_fr, _ = fr(issues_redressements)
    sauves, sauves_fr = iss.get("plan ou sauvetage", float("nan")), iss_fr["plan ou sauvetage"]

    def compare(v, v_fr, fmt, plus_mauvais):
        if not filtre_actif or v != v:
            return None
        sens = "up" if (v > v_fr) == plus_mauvais else "down"
        return (f"France : {fmt(v_fr)}", sens)

    ecart = lambda v: "—" if v != v else f"{'+' if v >= 100 else '−'}{abs(v - 100):.0f} %"
    tendance = ecart(ind)
    tuiles = [
        ("Risque de défaillance (2025)", pour_mille(t), "des entreprises actives ont fait défaillance" +
         ("" if filtre_actif else " · 6,3 ‰ en 2009"), compare(t, t_fr, pour_mille, True), "/secteurs"),
        ("Les 12 derniers mois", tendance, "par rapport à un mois normal (2010-2019)",
         compare(ind, ind_fr, ecart, True), "/evenements"),
        ("Liquidées d'emblée", pct(lj), "des entreprises en procédure, sans tentative de sauvetage",
         compare(lj, lj_fr, pct, True), "/parcours"),
        ("Redressements sauvés", pct(sauves), "plan ou sauvetage dans les 36 mois (2008-2023)",
         compare(sauves, sauves_fr, pct, False), "/parcours"),
    ]
    cols = [dbc.Col(dcc.Link(chiffre_cle(lib, val, det, evo), href=lien, className="ds-link-card"), md=6, xl=3,
                    className="mb-3") for lib, val, det, evo, lien in tuiles]
    r = risque_profils(secteur, region)
    if r["exercices"].sum() == 0:
        signal = [html.B("Le signal à surveiller : la trésorerie. "), "Pas de comptes publiés dans ce périmètre ; en France, "
                  "les entreprises « en perte, capitaux propres négatifs » font faillite dans 6,8 % des cas dans les 3 ans, "
                  "contre 1,3 % pour les plus solides. ", dcc.Link("Signaux financiers →", href="/signaux")]
    else:
        signal = [html.B("Le signal à surveiller : la trésorerie. "),
                  "Dans les comptes, les entreprises « en perte, capitaux propres négatifs » font faillite dans ",
                  html.B(pct(r.at[3, "taux"], 1)), " des cas dans les 3 ans, contre ", pct(r.loc[[1, 2], "taux"].min(), 1),
                  " pour les plus sûres", (" (France : 6,8 % contre 1,3 %)." if filtre_actif else "."),
                  " ", dcc.Link("Signaux financiers →", href="/signaux")]
    prudence = None
    if filtre_actif and (n_rj < 200 or r["faillites"].sum() < 100):
        prudence = (f"Attention, petit périmètre : {nombre(n_rj)} redressements et {nombre(r['faillites'].sum())} "
                    "faillites dans les comptes. Les pourcentages varient beaucoup d'un cas à l'autre.")
    return html.Div([dbc.Row(cols), encart_perimetre("Dans les comptes", *signal, prudence=prudence)])


@callback(Output("ac-filrouge-titre", "children"), Output("ac-filrouge-texte", "children"),
          Output("ac-solde", "figure"), Output("ac-pour-vous", "children"),
          Input("filtre-secteur", "value"), Input("filtre-region", "value"))
def maj_accueil(secteur, region):
    perimetre = libelle_perimetre(secteur, region)
    b = bilan_rattrapage(secteur, region)
    titre = ("Le fil rouge : le Covid a gelé les faillites, et le rattrapage n'est pas fini" if not est_filtre(secteur, region)
             else f"Le fil rouge, pour « {perimetre} »")
    return titre, texte_fil_rouge(b, perimetre), figure_solde(secteur, region), tuiles_pour_vous(secteur, region)


def layout():
    return html.Div([
        entete("Les défaillances d'entreprises en France",
               "Ce que disent 19 ans d'annonces de procédures collectives (BODACC), le répertoire des entreprises (SIRENE) "
               "et leurs comptes (ratios BCE / INPI). Choisissez votre secteur et votre région dans la barre de gauche : "
               "les chiffres marqués « périmètre » s'adaptent.",
               surtitre="Projet M2 · Analyse de données",
               badges=[badge("BODACC 2008-2026"), badge("SIRENE : 30 M d'entreprises"), badge("Ratios BCE / INPI")]),

        html.H2(id="ac-filrouge-titre", className="ds-filrouge__titre"),
        html.P(id="ac-filrouge-texte", className="ds-filrouge__texte"),
        carte(graphe("ac-solde", hauteur=360),
              titre="Défaillances en plus ou en moins que la normale, cumulées depuis janvier 2020",
              description="Chaque mois, on compare au même mois des années 2010 à 2019, puis on additionne les écarts. "
                          "La courbe descend quand il y a moins de défaillances que d'habitude, remonte quand il y en a plus.",
              pied="Source : BODACC. Détail sur la page « Événements de masse ».", className="mb-4"),
        methode(html.Ul([
            html.Li("Normale d'un mois = moyenne du même mois de 2010 à 2019, calculée pour le périmètre choisi."),
            html.Li("Solde = somme des écarts (défaillances du mois − normale) depuis janvier 2020. « Manquantes » = solde "
                    "fin août 2022, à la fin de l'épisode Covid ; « rattrapées » = écarts cumulés depuis septembre 2022."),
            html.Li("Limite : un secteur qui faisait beaucoup faillite dans les années 2010 (la construction, par exemple) "
                    "peut rester sous sa normale sans qu'il s'agisse d'un gel : la normale elle-même a pu baisser."),
            html.Li("Les données sont agrégées avec un cube OLAP (DuckDB) : un comptage par mois, secteur et région, "
                    "puis on réunit les cases du périmètre choisi (opération de « roll-up »)."),
        ], className="ds-list")),

        html.H2("Et pour vous ?", className="ds-section__titre", style={"marginTop": "28px"}),
        html.P("Quatre repères pour un dirigeant, un banquier ou un expert-comptable : le risque, la tendance, et ce qui "
               "arrive quand une procédure s'ouvre. Flèche ▲ : plus défavorable que la moyenne française.",
               className="ds-section__intro"),
        html.Div(id="ac-pour-vous", className="mb-4"),

        html.H2("Ce qu'il faut retenir", className="ds-section__titre", style={"marginTop": "28px"}),
        html.P("À l'échelle de la France. Chaque carte mène à la page qui le démontre.", className="ds-section__intro"),
        dbc.Row([dbc.Col(reponse_cle(texte, lien, page), md=6, xl=3, className="mb-4") for texte, lien, page in RETENIR]),
    ])
