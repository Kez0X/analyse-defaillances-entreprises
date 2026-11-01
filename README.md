# Défaillances d'entreprises en France : qui fait faillite, où, et pourquoi ?

Projet d'Analyse de Données (M2).

## 1. Le projet

### La question

> **Quels secteurs, territoires et profils d'entreprises concentrent les défaillances
> en France, et comment ce risque évolue-t-il dans le temps ?**

**Pour qui ?** Un courtier en assurance ou un assureur d'entreprises. Ils ont besoin de
mesurer et d'anticiper le risque de défaillance de leurs clients et prospects :
- en **assurance-crédit**, pour protéger un client contre l'impayé de ses propres clients ;
- pour analyser la fragilité de leur **propre portefeuille** ;
- pour le **conseil** aux entreprises.

**Livrable final :** un dashboard de KPI et d'analyses graphiques.

### Les données

Trois sources publiques, reliées par le numéro **SIREN** de l'entreprise :

| Source | Ce qu'elle apporte | Volume |
|---|---|---|
| **BODACC** (DILA) | Les annonces légales de procédures collectives depuis 2008 : quelle entreprise, quand, où, quel jugement | ~120 000 à 200 000 annonces par an |
| **SIRENE** (Insee) | Le répertoire de toutes les entreprises : secteur, date de création, taille, forme juridique, état | 30 M+ d'unités légales |
| **Ratios financiers BCE / INPI** | Les indicateurs tirés des comptes annuels : chiffre d'affaires, rentabilité, endettement, liquidité | ~7 M de bilans (2016-2025 surtout) |

SIRENE sert aussi de **dénominateur** : rapporter le nombre de défaillances au nombre
d'entreprises actives permet de calculer des **taux**, et pas seulement des volumes.

### La démarche

L'analyse se fait **étape par étape**. Chaque choix (définitions, nettoyage, variables,
paramètres) est discuté et justifié avant de passer à la suite.

1. [ ] **Exploration** : découverte des sources, volumes, types, valeurs manquantes
2. [ ] **Définition et nettoyage** : ce qu'on compte comme défaillance, dédoublonnage, jointures entre sources
3. [ ] **Transformation** : variables dérivées (âge de l'entreprise, secteur, taille…), encodage, normalisation
4. [ ] **Agrégation / OLAP** : schéma en étoile, cubes (temps × secteur × territoire × profil), KPI
5. [ ] **Clustering** : profils d'entreprises défaillantes, ou typologie des secteurs et territoires
6. [ ] **Fouille de données** : règles d'association sur les profils à risque
7. [ ] **Dashboard** : restitution des KPI et des analyses

### Points d'attention connus dès le départ

- **Une annonce n'est pas une défaillance** : une même entreprise peut faire l'objet de plusieurs annonces (ouverture, conversion, plan, clôture…).
- **Biais de couverture des ratios** : beaucoup de petites entreprises ne déposent pas leurs comptes ou les rendent confidentiels.
- **Effet Covid** : les défaillances ont chuté en 2020-2021 grâce aux aides publiques, puis ont rattrapé leur retard ensuite.
- **Données personnelles** : les entrepreneurs individuels sont des personnes physiques. Les données brutes ne sont pas versionnées dans ce dépôt, et le statut de diffusion SIRENE doit être respecté.

## 2. Vocabulaire

### Droit des entreprises en difficulté

| Terme | Définition |
|---|---|
| **Cessation des paiements** | Situation d'une entreprise qui ne peut plus faire face à ses dettes exigibles avec son actif disponible. Elle déclenche l'obligation de demander l'ouverture d'une procédure dans les 45 jours. |
| **Procédure collective** | Procédure judiciaire qui organise le traitement des difficultés d'une entreprise sous le contrôle du tribunal. Elle suspend les poursuites individuelles des créanciers. Il y en a trois : sauvegarde, redressement, liquidation. |
| **Sauvegarde** | Procédure *préventive*, ouverte à la demande d'une entreprise en difficulté mais **pas encore en cessation des paiements**. |
| **Redressement judiciaire (RJ)** | Procédure ouverte pour une entreprise **en cessation des paiements** dont le redressement semble possible. Elle aboutit à un plan de redressement, une cession ou une liquidation. |
| **Liquidation judiciaire (LJ)** | Procédure ouverte quand le redressement est **manifestement impossible**. L'activité s'arrête et les actifs sont vendus pour payer les créanciers. |
| **Jugement d'ouverture** | Décision du tribunal qui ouvre une procédure collective. C'est l'**événement de référence** pour dater une défaillance. |
| **Conversion** | Passage d'une procédure à une autre en cours de route, par exemple d'un redressement en liquidation. |
| **Plan de sauvegarde / de redressement** | Plan d'apurement des dettes (jusqu'à 10 ans) arrêté par le tribunal, qui permet à l'entreprise de poursuivre son activité. |
| **Clôture pour insuffisance d'actif** | Fin d'une liquidation quand les actifs ne suffisent pas à payer les créanciers. C'est la fin juridique de l'entreprise. |
| **Défaillance d'entreprise** | Au sens de la Banque de France : **ouverture d'une procédure de redressement ou de liquidation judiciaire**, les sauvegardes n'étant pas comptées. C'est une définition de référence, la définition retenue dans le projet sera fixée à l'étape 2. |
| **Assurance-crédit** | Assurance qui couvre une entreprise contre le risque de non-paiement de ses clients, notamment en cas de défaillance de ceux-ci. |

### Sources et identifiants

| Terme | Définition |
|---|---|
| **BODACC** | *Bulletin officiel des annonces civiles et commerciales*. Journal officiel où sont publiés les événements de la vie des entreprises : immatriculations, ventes, procédures collectives, radiations… |
| **SIRENE** | *Système informatique pour le répertoire des entreprises et de leurs établissements*, tenu par l'Insee. |
| **Unité légale** | L'entreprise en tant qu'entité juridique : une société ou un entrepreneur individuel. Elle est identifiée par son **SIREN** (9 chiffres). |
| **Établissement** | Un lieu d'activité physique d'une unité légale (siège, agence, usine…). Il est identifié par son **SIRET** (SIREN + 5 chiffres). Une unité légale a un ou plusieurs établissements. |
| **Personne morale / physique** | Une société (SARL, SAS…) est une personne morale. Un entrepreneur individuel exerce en son nom propre : c'est une personne physique. |
| **Code NAF / APE** | Code d'activité principale de la *Nomenclature d'activités française*. Il est hiérarchique : section (21 postes, ex. F « Construction ») > division > groupe > classe > sous-classe (732 postes). |
| **Catégorie juridique** | La forme juridique de l'entreprise : SAS, SARL, entrepreneur individuel, association… |
| **Tranche d'effectif** | Classe du nombre de salariés (0, 1-2, 3-5, 6-9, 10-19…). |
| **Catégorie d'entreprise** | Taille au sens de la loi LME : **PME** (moins de 250 salariés), **ETI** (250 à 4 999), **GE** (grande entreprise). |
| **Taux de défaillance** | Nombre de défaillances sur une période rapporté au nombre d'entreprises actives sur cette période. |

### Indicateurs financiers (ratios BCE / INPI)

Les formules exactes utilisées par l'INPI seront vérifiées dans la documentation de la
source avant toute interprétation.

| Terme | Définition |
|---|---|
| **Chiffre d'affaires (CA)** | Montant des ventes de biens et services sur l'exercice. |
| **EBE** (excédent brut d'exploitation) | Ce que l'activité génère avant amortissements, charges financières et impôts. C'est la rentabilité « opérationnelle » brute. |
| **Résultat net** | Bénéfice ou perte final de l'exercice. |
| **Taux d'endettement** | Poids des dettes financières par rapport aux capitaux propres. |
| **Ratio de liquidité** | Capacité à payer les dettes de court terme avec les actifs de court terme. |
| **Autonomie financière** | Part des capitaux propres dans le total du bilan. |
| **BFR** (besoin en fonds de roulement) | Argent immobilisé par le cycle d'exploitation : stocks + créances clients − dettes fournisseurs. |
| **Délais clients / fournisseurs** | Nombre moyen de jours pour être payé par ses clients, ou pour payer ses fournisseurs. |
| **Exercice / date de clôture** | La période comptable (souvent 12 mois) et sa date de fin. |

### Analyse de données

| Terme | Définition |
|---|---|
| **Fait / mesure** | L'événement observé (une défaillance) et ce qu'on y mesure (nombre, taux, emplois concernés…). |
| **Dimension / hiérarchie** | Un axe d'analyse (temps, secteur, territoire) et ses niveaux (année > trimestre > mois, région > département > commune). |
| **Schéma en étoile** | Une table de faits centrale reliée à des tables de dimensions. |
| **Cube OLAP** | Une structure qui agrège les mesures selon plusieurs dimensions à la fois. |
| **Roll-up / drill-down** | Remonter ou descendre dans une hiérarchie, par exemple du département à la région. |
| **Slice / dice** | Fixer la valeur d'une dimension (slice) ou restreindre plusieurs dimensions (dice). |
| **Clustering** | Regroupement non supervisé d'individus similaires (k-means, DBSCAN, CAH…). |
| **Règle d'association** | Une règle « si A alors B » extraite des données, évaluée par son **support** (fréquence de A et B ensemble), sa **confiance** (P(B \| A)) et son **lift** (confiance / P(B) : au-dessus de 1, A et B sont liés positivement). |

## 3. Usage de l'IA et précautions

Ce projet est réalisé avec l'aide d'un assistant IA (**Claude**, Anthropic), utilisé
comme **outil d'assistance** et non comme auteur de l'analyse.

### Ce que l'IA a fait ou peut faire

- Proposer des pistes de sujets et des sources de données publiques.
- Écrire le code technique, par exemple le script de téléchargement des données.
- Aider à rédiger la documentation, dont ce README.
- Expliquer des méthodes, proposer des options et signaler des points d'attention.

### Ce qui relève de l'étudiant

- Le **choix du sujet** et de la question posée.
- Toutes les **décisions d'analyse** : la définition d'une défaillance, les règles de nettoyage, le choix des variables, des méthodes et de leurs paramètres (nombre de clusters, seuils de support…).
- L'**interprétation** des résultats et les **conclusions**.

### Précautions prises

- **Vérification** : tout code produit avec l'aide de l'IA est relu, exécuté et contrôlé sur les données (volumes, cohérence) avant d'être utilisé.
- **Pas de chiffre « inventé »** : tous les chiffres présentés sont calculés à partir des données. Une IA peut produire des affirmations fausses mais plausibles (*hallucinations*), donc aucune valeur n'est reprise de ses réponses sans calcul.
- **Définitions sourcées** : les définitions juridiques et financières sont vérifiées auprès des sources officielles (Code de commerce, Insee, Banque de France, documentation INPI).
- **Données** : seules des données publiques sont utilisées. Aucune donnée confidentielle ou interne à une entreprise n'est transmise à l'IA.
- **Biais** : l'IA peut orienter l'analyse vers des approches « standard ». Les options proposées sont discutées, et le choix final est justifié dans les notebooks.
- **Traçabilité** : les décisions prises à chaque étape sont consignées dans les notebooks, avec leur justification.

### Le process

Dans un premier temps on va chercher à comprendre la data donc pour ce faire, nous allons détailler l'ordre des étapes selon lesquelles nous avons procédé : 
1. Analyse des fichiers BODACC, SIRENE, RATIOS
2. Une fois l'analyse ok, on va venir nettoyer les données

## Annexe : mise en route

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python scripts/download_data.py                                 # tout (~2 Go sur disque)
python scripts/download_data.py --only bodacc --years 2015-2025 # BODACC sur une période seulement
python scripts/download_data.py --only sirene --with-etablissements  # + établissements (~3 Go)
python scripts/download_data.py --force                         # re-télécharger
```

| Source | Fichier(s) | Volume | Durée indicative |
|---|---|---|---|
| BODACC | `data/raw/bodacc/procedures_collectives_<année>.csv.gz` | ~600 Mo | ~15 min |
| SIRENE | `data/raw/sirene/StockUniteLegale_utf8.zip`, dictionnaire dans `docs/sirene/` | ~1 Go | selon la connexion |
| Ratios | `data/raw/ratios/ratios_inpi_bce.csv.gz` | ~930 Mo brut, compressé | ~20-25 min |

```
projet_defaillances/
├── data/raw/          # données brutes (non versionnées)
├── data/processed/    # données transformées (non versionnées)
├── docs/              # dictionnaires des variables
├── notebooks/         # analyses étape par étape
└── scripts/           # récupération des données
```

**Sources et licences** (toutes sous Licence Ouverte / Open Licence v2.0, Etalab) :
- [BODACC, DILA](https://bodacc-datadila.opendatasoft.com/explore/dataset/annonces-commerciales/)
- [Base Sirene, Insee](https://www.data.gouv.fr/fr/datasets/base-sirene-des-entreprises-et-de-leurs-etablissements-siren-siret/)
- [Ratios financiers BCE/INPI](https://data.economie.gouv.fr/explore/dataset/ratios_inpi_bce/)
