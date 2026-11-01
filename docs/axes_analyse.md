# Axes d'analyse : défaillances d'entreprises

## Les données disponibles

Toutes dans `data/processed/`, produites par `notebooks/nettoyage.ipynb` :

| Fichier | Une ligne = | Ce qu'il permet |
|---|---|---|
| `bodacc_clean.parquet` | une annonce BODACC pour une entreprise (2008 → octobre 2026) | Compter les événements (entrées en défaillance, aggravations, issues, signaux précoces) dans le temps, par territoire, par tribunal |
| `sirene_clean.parquet` | une entreprise (30,1 M) | Décrire les entreprises (secteur, forme juridique, âge, département), et calculer des **taux** (défaillances / entreprises) |
| `ratios_clean.parquet` | un exercice comptable (clôturé entre 2016 et octobre 2026) | Décrire la santé financière des entreprises |
| `panel_exercices.parquet` | un exercice comptable clôturé avant novembre 2023, avec l'étiquette « faillite dans les 36 mois » | Le clustering et la fouille de données |

## Comment le projet est organisé

Le cœur du projet, ce sont les méthodes vues en cours : **réseaux** (Cours 3), **clustering** (Cours 2) et **transformation des données** (Cours 4). Autour :

| Partie | Rôle | Méthodes |
|---|---|---|
| **A. Exploration** | Connaître les données, préparer les parties B et C | Statistiques descriptives, tests (TP1), **cube OLAP** comme outil d'exploration et de pré-agrégation |
| **B. Graphes** | **Axe principal** | Centralités, PageRank, communautés de Louvain, Gephi (Cours 3, TP3), similarité → graphe → node2vec (TP4) |
| **C. Clustering et transformation** | **Axe principal** | k-means, mélange gaussien, DBSCAN, silhouette (Cours 2, TP2), ACP, t-SNE (Cours 4, TP4) |
| **D. Bonus : fouille de données supervisée** | Curiosité : prédire la faillite | Classification supervisée |

---

# Partie A : exploration

Ces axes servent à bien connaître les données. Ils fournissent aussi les tableaux pré-agrégés qui alimentent les graphes et les clusters.

## Le cube OLAP : un outil d'exploration et de pré-agrégation

On ne fait pas du cube un axe d'analyse à part. On s'en sert pour :
- **explorer** rapidement : faire des coupes (une année, un secteur) et passer d'un niveau à l'autre (année → mois, région → département) ;
- **pré-agréger** les comptages une bonne fois pour toutes, au lieu de relire 3,3 M de lignes à chaque analyse. Par exemple, le nombre d'entrées en défaillance par **mois × division NAF × département** sert directement à construire les graphes des axes 7 et 8 et les clusters de l'axe 10.

**Table de faits** : les événements BODACC (une ligne par événement et par entreprise).

**Mesures** :
- nombre d'entrées en défaillance, d'aggravations, d'issues, de signaux précoces ;
- nombre d'entreprises distinctes ;
- taux de défaillance (rapporté au nombre d'entreprises actives).

**Dimensions** :

| Dimension | Niveaux |
|---|---|
| Temps | année → trimestre → mois |
| Territoire | région → département → tribunal |
| Secteur | section NAF → division NAF |
| Forme juridique | famille → catégorie juridique |
| Âge | tranche d'âge à la date du jugement |
| Taille | tranche de chiffre d'affaires (seulement si l'entreprise a des ratios) |
| Type d'événement | catégorie → nature du jugement |
| Type de personne | personne morale / personne physique / sans SIREN |

Mise en œuvre possible : des `groupby` pandas enregistrés en parquet. On peut aussi utiliser DuckDB, qui sait calculer directement tous les sous-totaux avec `GROUP BY CUBE (...)`.

## Axe 1 : l'évolution dans le temps

Questions :
- Comment évolue le nombre d'**entrées en défaillance** par an et par mois depuis 2008 ?
- Quel a été l'effet du **Covid** (2020-2021) ? Y a-t-il eu un **rattrapage** ensuite (2023-2025), qui dépasse le niveau d'avant crise ?
- Y a-t-il une **saisonnalité** ?
- La part des **liquidations directes** par rapport aux **redressements** change-t-elle dans le temps ?
- Les **signaux précoces** (sauvegardes) augmentent-ils avant une hausse des défaillances ?

⚠️ 2026 s'arrête fin octobre : on la compare à janvier-octobre des autres années. La rupture Covid est toujours signalée.

## Axe 2 : le territoire

Questions :
- Quels **départements** et **régions** ont le plus de défaillances, en nombre et en **taux** ?
- Les écarts entre territoires sont-ils stables dans le temps ? Certains ont-ils été plus touchés par le Covid ou par le rattrapage ?
- Y a-t-il des différences entre **tribunaux** (par exemple plus de liquidations directes dans certains) ?
- L'outre-mer se comporte-t-il différemment de la métropole ?

⚠️ Pour un taux, il faut le nombre d'entreprises **actives à l'époque**, alors que SIRENE donne la situation actuelle. On peut l'estimer avec les dates de création et de cessation.

## Axe 3 : le secteur d'activité

Questions :
- Quels **secteurs** (section NAF, puis division) ont le plus de défaillances, en nombre et en taux ?
- Quels secteurs ont été les plus **protégés** pendant le Covid, et lesquels rattrapent le plus depuis ?
- Dans quels secteurs finit-on le plus souvent en **liquidation directe** ?

## Axe 4 : le profil de l'entreprise (forme juridique, âge, taille)

Questions :
- **Forme juridique** : les SAS font-elles plus ou moins faillite que les SARL ? Et les entrepreneurs individuels ?
- **Âge** : les entreprises jeunes font-elles plus faillite ? Y a-t-il un âge « critique » ?
- **Taille** (chiffre d'affaires) : les petites entreprises sont-elles plus fragiles ?
- Les entreprises **déjà passées par une défaillance** refont-elles faillite plus souvent ?

⚠️ La taille n'est connue que pour environ 18 % des entreprises du BODACC, presque toutes des sociétés commerciales.

## Axe 5 : la santé financière avant la faillite

Questions :
- Les entreprises qui vont faire faillite ont-elles des ratios différents des autres **1, 2 ou 3 ans avant** ? Lesquels ?
- À partir de **quand** les ratios se dégradent-ils ?
- Est-ce que **ne plus déposer ses comptes** est un signe de difficulté ?
- Les ratios sont-ils liés entre eux (corrélations de **Spearman**) ?

Méthodes (TP1) : distributions, boîtes à moustaches, tests statistiques (normalité, comparaison de groupes), corrélations.

---

# Partie B : graphes (axe principal)

## Axe 6 : le graphe des parcours de procédure

**Idée** : un **nœud par étape** (sauvegarde, redressement, liquidation, plan de redressement, plan de cession, clôture…) et une **flèche pondérée** par le nombre d'entreprises qui passent d'une étape à la suivante. Le graphe est construit en suivant les événements de chaque entreprise dans `bodacc_clean`.

Questions :
- Quels **chemins** mènent le plus souvent à la liquidation ? Quelle part des redressements finit en plan, en cession ou en liquidation ?
- Quelles étapes sont des **carrefours** (centralités, PageRank) ?
- Le graphe change-t-il **avant et après le Covid**, ou selon le secteur ?
- Combien de temps dure chaque passage (on peut mettre la durée moyenne sur les flèches) ?

Méthodes : graphe orienté pondéré (networkx), centralités, PageRank, visualisation dans Gephi.

⚠️ Une procédure ouverte récemment n'est peut-être pas encore terminée.

## Axe 7 : le graphe des entreprises liées

**Idée** : deux entreprises sont **reliées** si elles sont citées dans la **même annonce** (annonces collectives, extensions de procédure : 23 065 lignes concernées).

Questions :
- Combien de **composantes connexes**, et de quelle taille ? Retrouve-t-on des **groupes de sociétés** ?
- Les **communautés de Louvain** correspondent-elles à des groupes, à des secteurs, à des territoires ?
- Quelles entreprises sont **centrales** (degré, intermédiarité) ? Sont-ce des maisons mères ?
- Une défaillance se **propage**-t-elle dans un groupe ?

Méthodes : networkx, composantes connexes, centralités, Louvain, Gephi.

## Axe 8 : le graphe des secteurs qui « souffrent ensemble »

**Idée** (même méthode que le TP4) : pour chaque division NAF, on prend la **courbe mensuelle** des entrées en défaillance (venant du cube). On calcule la **similarité cosinus** entre les courbes, on garde les liens forts (seuil), et on obtient un graphe de secteurs.

Questions :
- Quels secteurs **réagissent de la même façon** aux crises (Covid, rattrapage) ?
- Les **communautés de Louvain** regroupent-elles des secteurs proches dans la nomenclature, ou des secteurs très différents ?
- Le graphe est-il **small world** ?
- Que donne un plongement **node2vec** de ce graphe, ramené en 2D ?

## Axe 9 : le graphe des départements

**Idée** : la même chose pour les **départements**, avec leurs courbes de défaillance dans le temps, ou leur répartition par secteur.

Questions :
- Y a-t-il des **zones** qui vivent les mêmes cycles de défaillance ?
- Les **communautés** sont-elles **géographiques** (départements voisins) ou non ? On les affiche sur une **carte**, comme les aéroports du TP3.
- L'effet de la résolution de Louvain sur le nombre de communautés.

---

# Partie C : clustering et transformation (axe principal)

## Axe 10 : les profils financiers des entreprises

**Idée** : regrouper les exercices qui se ressemblent financièrement **sans utiliser l'étiquette « faillite »**, puis regarder où tombent les faillites.

Questions :
- Les ratios sont-ils redondants ? Combien d'axes d'**ACP** suffisent à les résumer, et que représentent ces axes ?
- Quels **grands profils** ressortent avec **k-means** (par exemple « rentable et peu endettée », « en perte et sans trésorerie ») ? Combien de clusters choisir (**silhouette**, méthode du coude) ?
- Le **mélange gaussien** donne-t-il les mêmes groupes ? Quelles entreprises sont **entre deux profils** ?
- **DBSCAN** : quelles entreprises sont classées comme **bruit** ? Sont-ce des profils atypiques, ou des valeurs ramenées par la winsorisation ?
- Dans quels clusters la **faillite dans les 36 mois** est-elle la plus fréquente ?
- Un **t-SNE** coloré par l'étiquette « faillite » montre-t-il une zone à part pour les entreprises qui vont faire faillite ?

Méthodes : normalisation, ACP, k-means, mélange gaussien, DBSCAN, silhouette, interprétation des centres (TP2), t-SNE (TP4).

⚠️ 5 M d'exercices, c'est trop pour la RAM et pour DBSCAN ou t-SNE : on travaille sur un **échantillon**, par exemple un exercice par entreprise ou un tirage aléatoire.

## Axe 11 : typologie des secteurs et des départements

**Idée** : décrire chaque secteur ou département par quelques indicateurs pris dans le cube (taux de défaillance, part de liquidations directes, effet Covid, rattrapage), puis les regrouper par clustering.

Questions :
- Quels **types** de secteurs ou de départements ressortent ?
- Ces groupes ressemblent-ils aux **communautés** trouvées avec les graphes des axes 8 et 9 ?

---

# Partie D : bonus, fouille de données supervisée

## Axe 12 : prédire la faillite

C'est de la **curiosité** : voir comment on implémente un modèle qui prédit la faillite. Ce n'est pas le cœur du projet.

Questions :
- Peut-on prédire `faillite_36_mois` avec les ratios, le secteur, la forme juridique et l'âge ? Avec quelle qualité ?
- Quelles **variables** comptent le plus ?
- Un modèle simple et lisible (régression logistique, arbre de décision) fait-il presque aussi bien qu'un modèle plus complexe (forêt aléatoire, gradient boosting) ?
- Les **clusters** de l'axe 10, utilisés comme variable, aident-ils le modèle ?

Étapes de mise en œuvre :
1. **Échantillon** : garder tous les exercices « faillite » et un tirage des autres, pour tenir en RAM.
2. **Découpage apprentissage / test** : par **entreprise** (une même entreprise ne doit pas être des deux côtés), ou par **année** (apprendre sur 2016-2020, tester sur 2021-2023), ce qui ressemble plus à une vraie prédiction.
3. **Variables** : ratios, colonnes `_ramene`, âge, secteur et forme juridique (encodés), `deja_defaillante`.
4. **Déséquilibre** (1,9 % de faillites) : pondérer les classes ou rééquilibrer l'échantillon d'apprentissage.
5. **Modèles** : régression logistique, arbre de décision, forêt aléatoire, gradient boosting (scikit-learn).
6. **Évaluation** : rappel, précision, courbe ROC et AUC. Le taux de bonnes réponses ne veut rien dire ici : un modèle qui répond toujours « pas de faillite » aurait 98 % de bonnes réponses.
7. **Interprétation** : importance des variables, lecture de l'arbre de décision.

---

# Le rendu : un dashboard Dash

La consigne : appliquer **au moins la moitié des TP** sur un jeu de données réel et restituer le tout dans un **dashboard Dash**. C'est un « petit » projet : il n'est pas demandé d'aller plus loin dans l'analyse.

## Les TP couverts

| TP | Où on l'applique |
|---|---|
| TP1 : exploration, nettoyage, statistiques | Notebooks d'exploration et de nettoyage (déjà faits), partie A |
| TP2 : clustering | Axes 10 et 11 |
| TP3 : réseaux | Axes 6 à 9 |
| TP4 : transformation (ACP, t-SNE, similarité → graphe → node2vec) | Axes 8 et 10 |

## Une page du dashboard par partie

| Page | Contenu |
|---|---|
| Vue d'ensemble | Axes 1 à 4 : courbes, cartes et tableaux, avec des filtres (période, secteur, territoire) qui s'appuient sur le cube |
| Parcours des procédures | Axe 6 : le graphe des étapes |
| Réseaux | Axes 7 à 9 : graphes et communautés, carte des départements |
| Profils financiers | Axes 5, 10 et 11 : ACP, clusters, t-SNE, taux de faillite par cluster |
| Bonus : prédiction | Axe 12 |

## Répartition dans le binôme

| | Luka | Lucas |
|---|---|---|
| Analyses | **Cube OLAP**, graphes (axes 6 à 9), profils financiers et typologies (axes 10, 11), bonus (axe 12) | Analyses de base : vue d'ensemble (axes 1 à 4) et santé financière (axe 5) |
| TP appliqués | TP3 (réseaux), TP2 (clustering), TP4 (ACP, t-SNE, node2vec) | TP1 (statistiques descriptives, tests, visualisation) |
| Pages Dash | Parcours des procédures, Réseaux, Profils financiers, Prédiction | Vue d'ensemble |

À se mettre d'accord ensemble au début :
- l'**ossature de l'application Dash** (navigation entre les pages) ;
- le **format des fichiers de résultats** dans `data/dashboard/`.

Dépendance : les axes 1 à 4 de Lucas s'appuient sur le **cube** de Luka. Le cube est donc à faire **en premier**, pour que Lucas puisse avancer.

## Organisation technique

- Les **notebooks d'analyse** font les calculs lourds et **exportent des petits fichiers de résultats** (cube pré-agrégé, nœuds et arêtes des graphes, coordonnées ACP et t-SNE d'un échantillon, clusters) dans un dossier dédié, par exemple `data/dashboard/`.
- L'application Dash **ne lit que ces petits fichiers**. Elle ne doit jamais charger SIRENE ou les ratios complets, sinon elle sera lente et saturera la RAM.

---

## Limites à garder en tête pour toutes les analyses

- **Annonces sans SIREN** (9 %) : gardées pour les comptages dans le temps et par territoire, mais on ne peut pas les relier à SIRENE ni aux ratios.
- **Ratios** : seulement à partir de 2016, et presque uniquement pour des sociétés commerciales.
- **Taille** : connue seulement pour les entreprises qui ont des ratios. Les très grandes entreprises sont ramenées à la limite de la winsorisation (environ 77,6 M€).
- **2026 incomplète** (jusqu'à fin octobre), **rupture Covid** en 2020-2021.
- **SIRENE** donne la situation actuelle des entreprises, pas leur situation à la date de la faillite.
