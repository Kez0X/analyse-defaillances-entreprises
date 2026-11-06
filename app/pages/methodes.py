"""Méthodes utilisées : chaque méthode d'analyse de données du cours, ce qu'elle a apporté, et où la voir.

Page statique (pas de données lues) : les chiffres viennent des observations des notebooks de notebooks/axes/.
"""
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html

from design import badge, carte, entete

dash.register_page(__name__, path="/methodes", name="Méthodes utilisées", order=8, section="Analyses")

# (famille, [(méthode, à quoi elle sert ici, ce qu'elle a trouvé, page, lien)])
FAMILLES = [
    ("Organiser et explorer les données", "Avant toute analyse : réunir 3 sources et pouvoir les découper.", [
        ("Cube OLAP", "Compter les défaillances par année, mois, secteur, région, âge, forme juridique… toutes les "
         "combinaisons d'un coup (CUBE, ROLLUP), puis découper (slice) ou agréger (roll-up) à la demande.",
         "C'est lui qui fait marcher les filtres secteur et région de tout le dashboard, et les taux de défaillance "
         "(défaillances / entreprises actives).", "Vue d'ensemble, Accueil", "/vue-ensemble"),
        ("Fouille de données exploratoire", "Comparer chaque mois à sa « normale » (même mois de 2010-2019) pour "
         "repérer automatiquement ce qui sort de l'ordinaire.",
         "Un seul vrai choc (le Covid), une vague propre aux auxiliaires financiers, et des journées de masse dans "
         "les tribunaux depuis 2024.", "Événements de masse", "/evenements"),
    ]),
    ("Réduire les dimensions", "13 ratios financiers, c'est trop pour les regarder ensemble.", [
        ("ACP (analyse en composantes principales)", "Résumer les 13 ratios en quelques axes, et vérifier s'ils se "
         "résument bien.", "Il faut 6 composantes pour dépasser 70 % de la variance : les ratios sont peu redondants, "
         "chacun apporte quelque chose.", "Signaux financiers", "/signaux"),
        ("t-SNE", "Dessiner sur un plan des points décrits par beaucoup de variables, en gardant les voisins proches.",
         "Carte de 5 000 entreprises : pas d'îlots séparés, un grand nuage où les faillites se concentrent dans une "
         "zone. Sert aussi à dessiner les plongements node2vec.", "Signaux financiers", "/signaux"),
    ]),
    ("Regrouper (clustering)", "Trouver des groupes sans savoir à l'avance lesquels.", [
        ("k-means", "Grouper les entreprises selon leurs ratios, puis les secteurs et départements selon 5 indicateurs.",
         "4 profils financiers, dont un (« en perte, capitaux propres négatifs ») qui fait 5 fois plus faillite. "
         "Typologie : les grandes agglomérations et l'Alsace à part (83 % de liquidations directes).",
         "Signaux financiers, Secteurs", "/signaux"),
        ("Silhouette et méthode du coude", "Choisir le nombre de groupes.",
         "Les deux ne sont pas d'accord (silhouette maximale à 2, coude à 5) : pas de groupes nets. On a retenu 4 "
         "parce qu'il sépare bien le risque.", "Signaux financiers", "/signaux"),
        ("Mélange gaussien", "Même idée que k-means, mais avec des groupes en forme de « cloche » et une probabilité "
         "d'appartenance.", "Groupes assez différents de k-means (ARI 0,31) : confirme que le découpage dépend de la "
         "méthode quand les groupes sont peu séparés.", "Signaux financiers (méthode)", "/signaux"),
        ("DBSCAN", "Trouver des zones denses et isoler les points atypiques (« bruit »).",
         "Un seul grand groupe et 3,6 % de bruit : il n'y a pas de familles d'entreprises nettement séparées.",
         "Signaux financiers (méthode)", "/signaux"),
        ("Classification hiérarchique (Ward)", "Construire un arbre de regroupements, pour vérifier k-means.",
         "Assez d'accord avec k-means (ARI 0,51 pour les secteurs, 0,62 pour les départements) : la typologie tient.",
         "Secteurs et territoires (méthode)", "/secteurs"),
    ]),
    ("Graphes", "Quand ce qui compte, ce sont les liens : entre étapes, entre secteurs, entre entreprises.", [
        ("Graphe orienté et PageRank", "Les étapes d'une procédure (ouverture, plan, liquidation…) reliées par les "
         "passages réels de 918 171 entreprises.", "2 entreprises sur 3 liquidées d'emblée ; 7 redressements sur 10 "
         "finissent en liquidation. PageRank : liquidation et clôture pour insuffisance d'actif concentrent 80 % du poids.",
         "Parcours des procédures", "/parcours"),
        ("Similarité → seuil → graphe", "Relier deux secteurs (ou départements) si leurs défaillances évoluent pareil "
         "(corrélation de Spearman sur 12 mois glissants), seuil choisi par la méthode du coude.",
         "Avant 2020, chaque secteur suit son rythme ; c'est le Covid qui les a synchronisés.",
         "Secteurs et territoires", "/secteurs"),
        ("Communautés de Louvain et modularité", "Découper le graphe en groupes très reliés entre eux ; le nombre "
         "de groupes est choisi par une règle (stabilité, modularité).",
         "4 communautés de secteurs (modularité 0,16) et 5 de départements (0,19) : des groupes réels mais "
         "peu tranchés, et dispersés sur la carte.", "Secteurs et territoires", "/secteurs"),
        ("Centralités et small world", "Repérer les secteurs « pivots » (degré, intermédiarité) et décrire la "
         "forme du réseau.", "Les deux graphes sont « small world » (σ = 1,8 et 2,1) ; les secteurs centraux sont "
         "surtout les plus gros.", "Secteurs et territoires (méthode)", "/secteurs"),
        ("node2vec", "Marches aléatoires sur le graphe, puis un vecteur par nœud (Word2Vec), dessiné avec t-SNE.",
         "63 % des voisins d'un secteur sur la carte sont dans sa communauté : les communautés se voient, mais se "
         "mélangent en partie.", "Secteurs et territoires (méthode)", "/secteurs"),
        ("Graphe des entreprises liées", "Relier les entreprises citées dans une même annonce (un groupe, des "
         "sociétés sœurs) et regarder quand elles défaillent.", "76 % des paires liées défaillent à moins d'un an "
         "d'écart, contre 10 % au hasard : la faillite se propage dans les groupes.",
         "Secteurs et territoires", "/secteurs"),
    ]),
    ("Prévoir (bonus)", "Passer de la description à la prédiction, sur des comptes jamais vus.", [
        ("Régression logistique, arbre de décision, gradient boosting", "Prévoir la faillite à 3 ans à partir des "
         "comptes, appris sur 2016-2020 et testé sur 2021-2023.", "AUC 0,83 ; en surveillant 10 % des entreprises, "
         "on repère 48 % des faillites.", "Signaux financiers", "/signaux"),
        ("Courbe ROC et importance par permutation", "Évaluer les modèles, et savoir quelles variables comptent.",
         "La trésorerie (liquidité) est de loin le premier signal ; la rentabilité compte beaucoup moins.",
         "Signaux financiers", "/signaux"),
    ]),
]


def carte_methode(nom, role, resultat, page, lien):
    return carte(
        html.H3(nom, className="ds-methode-cours__nom"),
        html.P([html.Span("Pour quoi faire ", className="ds-methode-cours__role"), html.Br(), role]),
        html.P([html.Span("Ce qu'elle a trouvé ", className="ds-methode-cours__role"), html.Br(), resultat]),
        html.P(dcc.Link(f"À voir : {page} →", href=lien)),
        className="ds-methode-cours",
    )


def layout():
    n = sum(len(m) for _, _, m in FAMILLES)
    blocs = []
    for titre, intro, methodes in FAMILLES:
        blocs += [
            html.H2(titre, className="ds-section__titre", style={"marginTop": "24px"}),
            html.P(intro, className="ds-section__intro"),
            dbc.Row([dbc.Col(carte_methode(*m), md=6, xl=4, className="mb-3") for m in methodes]),
        ]
    return html.Div([
        entete("Les méthodes utilisées",
               f"{n} méthodes d'analyse de données, chacune au service d'une question. Pour chacune : à quoi elle "
               "sert ici, ce qu'elle a trouvé, et la page où voir le résultat. Le détail (paramètres, choix, limites) "
               "est dans les blocs « Comment on l'a obtenu » de chaque page, et dans les notebooks.",
               surtitre="Analyses",
               badges=[badge("Cube OLAP", "accent"), badge("Clustering", "accent"), badge("Graphes", "accent"),
                       badge("Réduction de dimension", "accent")]),
        *blocs,
    ])
