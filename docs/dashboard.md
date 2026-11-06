# Le dashboard Dash : mode d'emploi

## Lancer l'application

Depuis la racine du projet :

```bash
.venv/bin/pip install -r requirements.txt   # la première fois
.venv/bin/python app/app.py
```

Puis ouvrir <http://127.0.0.1:8050> dans le navigateur. En mode debug, la page se recharge toute seule quand on modifie un fichier.

## Organisation

```
app/
├── app.py              # l'application : barre latérale + conteneur des pages
├── design.py           # design system côté Python : couleurs, thème plotly, composants
├── donnees.py          # lecture des fichiers de data/dashboard/ + fonction coupe()
├── assets/
│   ├── 0_bootstrap.min.css # Bootstrap enregistré en local : l'application marche sans Internet
│   └── design_system.css   # design system côté CSS (chargé automatiquement par Dash, après Bootstrap)
└── pages/              # une page = un fichier
    ├── accueil.py       # /                (commun : chiffres clés, « Ce qu'il faut retenir »)
    ├── vue_ensemble.py  # /vue-ensemble    (Lucas, axes 1 à 5)
    ├── evenements.py    # /evenements      (Luka, événements de masse)
    ├── parcours.py      # /parcours        (Luka, axe 6)
    ├── secteurs.py      # /secteurs        (Luka, axes 7, 8, 9 et 11)
    ├── signaux.py       # /signaux         (Luka, axes 10 et 12)
    └── design_system.py # /design-system   (référence visuelle, cachée de la barre latérale)
```

Chacun travaille dans **ses propres fichiers de pages** : on évite ainsi de se marcher dessus dans git.

## La règle d'or : l'application ne lit que `data/dashboard/`

Les calculs lourds se font dans les **notebooks**, qui **exportent de petits fichiers de résultats** dans `data/dashboard/`. L'application ne lit **que** ces fichiers, avec `donnees.lire("nom_du_fichier")`.

Elle ne doit **jamais** charger SIRENE, les ratios ou le BODACC complets : ce serait très lent, et ça saturerait la RAM.

## Les fichiers disponibles

### Produits par `notebooks/cube.ipynb` (pour la vue d'ensemble)

| Fichier | Contenu | Dimensions |
|---|---|---|
| `cube_principal` | Le cube : nombre d'événements et d'entreprises distinctes | `categorie`, `annee`, `region`, `naf_section`, `cj_famille`, `tranche_age`, `tranche_taille`, `type_personne` |
| `cube_temps` | Détail du temps | `categorie`, `nature`, `annee`, `trimestre`, `mois` |
| `cube_territoire` | Détail du territoire | `categorie`, `annee`, `region`, `departement`, `tribunal` |
| `cube_secteur` | Détail du secteur | `categorie`, `annee`, `naf_section`, `naf_division` |
| `actives` | Entreprises actives au 1er janvier | `annee`, `region`, `naf_section`, `cj_famille`, `tranche_age` |
| `taux` | Taux de défaillance en ‰ (`taux_pour_mille`) | `annee`, `region`, `naf_section`, `cj_famille`, `tranche_age` |
| `series_divisions_mois` | Entrées en défaillance par mois (lignes) et division NAF (colonnes) | — |
| `series_departements_mois` | Entrées en défaillance par mois (lignes) et département (colonnes) | — |
| `departements_regions` | Correspondance département → région | — |

### Produits par les notebooks de `notebooks/axes/` (pages de Luka)

| Fichiers | Notebook | Page |
|---|---|---|
| `evenements_*` | `evenements.ipynb` (événements de masse) | Événements de masse, accueil |
| `parcours_*` | `parcours.ipynb` (axe 6) | Parcours des procédures |
| `entreprises_liees_*` | `entreprises_liees.ipynb` (axe 7) | Secteurs et territoires (question 4) |
| `graphe_secteurs_*` | `graphe_secteurs.ipynb` (axe 8) | Secteurs et territoires (question 1) |
| `graphe_departements_*`, `departements.geojson` | `graphe_departements.ipynb` (axe 9) | Secteurs et territoires (méthode) |
| `profils_*` | `profils_financiers.ipynb` (axe 10) | Signaux financiers |
| `typologie_*` | `typologie.ipynb` (axe 11) | Secteurs et territoires (questions 2 et 3) |
| `prediction_*` | `prediction.ipynb` (axe 12) | Signaux financiers (question 3) |

Mesures des cubes : `nb_evenements` (nombre d'événements) et `nb_entreprises` (nombre d'entreprises distinctes).

### Lire un cube : la valeur « Total »

Dans un cube, `"Total"` veut dire « toutes les valeurs de cette dimension réunies ». Pour obtenir un chiffre, il faut donc fixer **chaque** dimension : soit à une valeur, soit à `"Total"`.

La fonction `coupe()` de `donnees.py` le fait pour nous. Toute dimension qu'on ne cite pas est mise à « Total », et une dimension passée à `None` garde toutes ses valeurs :

```python
from donnees import coupe

# Entrées en défaillance par année, tout le reste réuni
coupe("cube_principal", categorie="entrée en défaillance", annee=None)

# Par région en 2025
coupe("cube_principal", categorie="entrée en défaillance", annee="2025", region=None)

# Par année ET par section NAF
coupe("cube_principal", categorie="entrée en défaillance", annee=None, naf_section=None)

# Taux de défaillance par tranche d'âge en 2019
coupe("taux", annee="2019", tranche_age=None)
```

⚠️ `nb_entreprises` **ne s'additionne pas** : une entreprise peut avoir plusieurs événements. Pour un total, il faut toujours lire la ligne « Total » du cube, et ne pas faire la somme des lignes.

À savoir :
- `annee` est du texte (`"2025"`) ; pour un axe de graphique, le convertir en nombre avec `.astype(int)` ;
- 2007 (fin d'année seulement) et 2026 (jusqu'à fin octobre) sont **incomplètes** ;
- la taille n'est connue qu'à partir de 2017, et pour une petite partie des entreprises ;
- `donnees.py` fournit l'ordre des tranches (`ORDRE_AGE`, `ORDRE_TAILLE`) et les libellés (`NAF_SECTIONS`, `CJ_FAMILLES`).

## Ajouter un graphique ou une page

1. Dans le notebook d'analyse, **exporter** le résultat : `df.to_parquet("../data/dashboard/mon_resultat.parquet")`.
2. Dans la page, le **lire** avec `lire("mon_resultat")`.
3. Les identifiants des composants commencent par le **préfixe de la page** (`ve-` pour la vue d'ensemble, `pa-` pour le parcours, `re-` pour les réseaux, `pr-` pour les profils, `pd-` pour la prédiction), pour éviter les doublons entre pages.
4. Pour une nouvelle page : créer un fichier dans `app/pages/` avec `dash.register_page(__name__, path="/...", name="...", order=..., section="Analyses")` et une fonction `layout()`. Elle apparaît toute seule dans la barre latérale, dans sa rubrique (`Exploration`, `Analyses` ou `Bonus`). Sans `section`, la page existe mais n'est pas dans la barre latérale.

`pages/vue_ensemble.py` contient un exemple complet : une liste déroulante, des boutons, un graphique et le callback qui les relie.

## Le design system

La page **Design system** du dashboard montre toutes les couleurs, les composants et les règles. Elle n'est **pas dans la barre latérale** (c'est une référence interne, pas une page du rendu) : on l'ouvre directement à l'adresse <http://127.0.0.1:8050/design-system>. On ne choisit **jamais** une couleur ou une police à la main : on utilise ce qui est défini dans `app/design.py` et `app/assets/design_system.css`.

### Les composants (`from design import ...`)

| Composant | À quoi il sert |
|---|---|
| `entete(titre, sous_titre, surtitre, badges)` | L'en-tête de chaque page |
| `carte(*contenu, titre, description, pied)` | Le contenant de base : un graphique, un tableau, un texte. Le `pied` donne la source et les précautions |
| `graphe(id, figure, hauteur)` | Un graphique plotly aux bons réglages, à mettre dans une `carte` |
| `chiffre_cle(libelle, valeur, detail, evolution)` | Un chiffre clé (comme sur l'accueil) |
| `filtres(filtre(libelle, controle), ...)` | La barre de filtres, **au-dessus** des graphiques qu'elle pilote |
| `boutons_segmentes(id, options, valeur)` | Un choix court (2 à 4 options) |
| `badge(texte, variante)`, `encadre(texte, titre, variante)` | Pastilles et encadrés (note ou mise en garde) |
| `zone_covid(fig)` | Grise 2020-2021 sur un graphique par année |
| `couleurs_annees(annees, couleur)` | Met en pâle les années incomplètes (2007, 2026) |
| `nombre(n)` | Formate un nombre à la française (`60 911`) |
| `question(titre, reponse, *graphiques, numero)` | Un bloc « question → réponse en une phrase → graphique qui le prouve ». C'est la structure de toutes les pages d'analyse |
| `methode(*contenu)` | Bloc repliable « Comment on l'a obtenu » : le détail technique, fermé par défaut |
| `gris_sauf(n, indices)` | Couleurs d'un graphique : tout en gris sauf ce qu'on veut montrer |
| `figure_reseau(noeuds, aretes, ...)` | Dessine un réseau (liens en gris, nœuds colorés par groupe, infobulles) |
| `couleur_groupe(i)` | La couleur du groupe ou de la communauté n° i, dans l'ordre fixe des séries |
| `tableau(df)` | Un tableau aux couleurs du design system, qui défile s'il est trop large |

### Les couleurs

- **Le thème plotly « defaillances » s'applique tout seul** à tous les graphiques (police, fond, grille, barres fines aux bouts arrondis).
- **Séries** : `SERIES` dans un ordre fixe, vérifié pour le daltonisme. Les catégories d'événements ont leur couleur attitrée dans `COULEURS_CATEGORIES` : une catégorie garde toujours la même couleur, même quand on filtre.
- **`AUTRE`** (gris) pour « autre » ou « non renseigné ».
- **`SEQUENTIELLE`** (bleu, du clair au foncé) pour une quantité sur une carte ou une matrice ; **`DIVERGENTE`** (bleu ↔ gris ↔ rouge) pour un écart à une moyenne.
- **`STATUT`** (vert, jaune, orange, rouge) est **réservé** aux états et ne sert jamais pour une série.

### Les règles des graphiques

- Avec 2 séries ou plus : toujours une légende. Avec une seule : pas de légende, le titre suffit.
- Le texte reste en noir ou gris, jamais dans la couleur d'une série.
- Jamais deux axes verticaux différents sur un même graphique : on fait deux graphiques.
- Toujours des infobulles. La période Covid et les années incomplètes sont toujours signalées.

### Organiser une page par questions

Chaque page d'analyse suit la même logique, pour que le lecteur trouve **la réponse avant la méthode** :
1. une **question** en titre ;
2. la **réponse en une phrase**, avec le chiffre important en gras ;
3. **un seul graphique** qui la prouve, en grisant ce qui n'est pas l'essentiel (`gris_sauf`) ;
4. tout le détail technique en bas de page, dans `methode(...)`.

## Les filtres globaux : secteur et région

La barre latérale contient deux listes, **Secteur** (`filtre-secteur`, une section NAF ou `"tous"`) et **Région**
(`filtre-region`, une région ou `"tous"`). Le choix est gardé quand on change de page. Quand un filtre est actif,
un bandeau en haut de la page rappelle le périmètre et dit ce qu'il change sur la page (dictionnaire `PORTEE` de
`app/app.py` : à compléter si ta page utilise les filtres).

Pour qu'un graphique suive le périmètre :

```python
from dash import Input, Output, callback
from donnees import TOUS, est_filtre, libelle_perimetre, filtrer

@callback(Output("mon-graphe", "figure"), Input("filtre-secteur", "value"), Input("filtre-region", "value"))
def maj(secteur, region):
    df = filtrer(lire("mon_fichier"), secteur, region)   # colonnes naf_section et region attendues
    ...
```

Règles :
- la réponse nationale de la question reste écrite telle quelle ; le périmètre s'affiche **en dessous**, dans
  un encart (`zoom("id")` dans la page, rempli avec `encart_perimetre(libelle, *texte, prudence=...)`) ;
- dans le graphique, le périmètre est en couleur et la **France en gris** (`GRIS_FRANCE`) ou en trait de repère ;
- si les effectifs sont petits, le dire avec `prudence=` plutôt que de cacher le chiffre.

Fonctions prêtes dans `donnees.py` : `serie_perimetre` (défaillances par mois, normale, indice, solde cumulé),
`bilan_rattrapage`, `taux_perimetre`, `issues_redressements`, `part_liquidation_directe`, `delais_perimetre`,
`risque_profils`.

Fichiers par secteur × région : `evenements_mensuel_perimetre`, `parcours_premiere_ouverture`,
`parcours_cohortes_perimetre`, `parcours_delais_perimetre` (avec la valeur « Total »), `profils_risque_perimetre`.
