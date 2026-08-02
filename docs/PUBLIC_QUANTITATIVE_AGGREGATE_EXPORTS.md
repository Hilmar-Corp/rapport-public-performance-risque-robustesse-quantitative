# Exports quantitatifs publics agrégés

## Objet

Le répertoire `artifacts/candidates/v0.3.0/quantitative_aggregates`
contient le paquet quantitatif agrégé publié avec la release GitHub
`v0.3.0`.

Le nom historique `candidates` est conservé afin de préserver l’intégrité
des manifestes, des empreintes et des engagements déjà publiés. Ce nom de
répertoire ne qualifie plus le statut de la release.

Ces éléments complètent les métriques agrégées déjà publiées sans inclure
les séries quotidiennes, les entrées du modèle, les identifiants privés ni
les valeurs exactes de réglage.

## Architecture

Le paquet contient :

- un fichier de métadonnées ;
- un fichier JSON par domaine quantitatif ;
- un manifeste déterministe ;
- un registre `SHA256SUMS`.

Les 21 sections quantitatives couvertes sont :

- Probabilistic Sharpe Ratio ;
- Deflated Sharpe Ratio ;
- White Reality Check et Hansen SPA ;
- CSCV et Probability of Backtest Overfitting ;
- moving-block bootstrap ;
- stationnarité ;
- dérive de distribution ;
- régimes de marché ;
- coûts et délais d’exécution ;
- permutations placebo ;
- risques de queue ;
- backtesting de la VaR et de l’Expected Shortfall ;
- Sharpe corrigé de la dépendance temporelle ;
- Monte Carlo historique par blocs ;
- reverse stress historique ;
- reverse stress contrefactuel ;
- résilience des données ;
- sensibilité de configuration ;
- ablations anonymisées ;
- monitoring shadow ;
- profondeur, durée et récupération des drawdowns.

## Frontière propriétaire

Le packageur public reçoit un fichier déjà assaini. Il ne lit aucune source
privée et ne contient aucune logique d’extraction depuis le corpus interne.

Le validateur rejette notamment :

- les chemins privés ;
- les séries ou champs de position ;
- les probabilités propriétaires ;
- les identifiants de variables ou de variantes ;
- les seuils, coefficients et valeurs exactes de réglage ;
- les affirmations de validation indépendante ;
- les affirmations de readiness ou d’approbation non enregistrées.

## Statut

Le paquet a été publié avec la release GitHub `v0.3.0`.

Son emplacement historique sous `artifacts/candidates` est conservé pour
ne pas modifier les contenus engagés par manifeste et SHA-256.

`artifacts/latest` reste le paquet public de référence correspondant à
`v0.2.1`. Il ne constitue pas un alias de la release quantitative agrégée
`v0.3.0`. La release GitHub `v0.3.0` constitue le point officiel de
distribution de ce paquet.

Les résultats sont rétrospectifs, agrégés et ne constituent ni une
validation indépendante ni une promesse de performance future.

## Construction

    PYTHONPATH=src python tools/package_public_quantitative_aggregates.py build \
      --input /path/to/sanitized-aggregate.json \
      --output-dir artifacts/candidates/v0.3.0/quantitative_aggregates

## Vérification

    PYTHONPATH=src python tools/package_public_quantitative_aggregates.py verify \
      --output-dir artifacts/candidates/v0.3.0/quantitative_aggregates

## Statut quantitatif du paquet

Le paquet couvre 21 sections quantitatives et comporte 24 fichiers
contrôlés, incluant les 21 fichiers de résultats, les métadonnées, le
manifeste et `SHA256SUMS`.

Les résultats centraux publiés sont les suivants :

- 2 211 observations pour les statistiques principales ;
- 15 essais agrégés pour le Deflated Sharpe Ratio ;
- 2 000 rééchantillonnages pour les tests de multiple testing ;
- 4 configurations agrégées de sensibilité CSCV/PBO ;
- 11 benchmarks publics réconciliés ;
- 11 différentiels de CAGR positifs ;
- 2 comparaisons individuellement significatives au seuil de 5 %.

Les p-values empiriques enregistrées à la résolution minimale du
rééchantillonnage ne doivent pas être interprétées comme des zéros
mathématiques.

## Shadow live et validation de production

Nostra AI fonctionne en shadow live sur données réelles et sur
l’infrastructure de production. Le shadow live constitue une validation
interne de production en conditions réelles, avec fonctionnement,
contrôles et monitoring opérationnels.

Cette qualification ne signifie ni validation externe indépendante,
ni usage contractuel en production chez un client. Ces catégories de
preuve restent séparées.

## Interprétation contrôlée

Le dépôt constitue un paquet public de preuves quantitatives et
techniques inspectable, manifesté, vérifiable et adapté à une due
diligence, un sandbox ou un pilote contrôlé.

Les résultats sont rétrospectifs et ne constituent pas une promesse de
performance future. La significativité statistique est
benchmark-spécifique et n’est pas démontrée contre l’ensemble des
benchmarks.
