# Exports quantitatifs publics agrégés

## Objet

Le répertoire `artifacts/candidates/v0.3.0/quantitative_aggregates`
contient un paquet candidat d’éléments quantitatifs agrégés destiné à la
future release `v0.3.0`.

Ces éléments complètent les métriques agrégées déjà publiées sans inclure
les séries quotidiennes, les entrées du modèle, les identifiants privés ni
les valeurs exactes de réglage.

## Architecture

Le paquet contient :

- un fichier de métadonnées ;
- un fichier JSON par domaine quantitatif ;
- un manifeste déterministe ;
- un registre `SHA256SUMS`.

Les domaines couverts sont :

- stationnarité ;
- dérive de distribution ;
- régimes de marché ;
- coûts et délais d’exécution ;
- permutations placebo ;
- risques de queue ;
- Monte Carlo historique par blocs ;
- résilience des données ;
- sensibilité de configuration ;
- ablations anonymisées ;
- monitoring shadow.

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

Le paquet est un candidat de release. Il ne doit pas être assimilé à
`artifacts/latest` avant la création contrôlée de `v0.3.0`.

Les résultats sont rétrospectifs, agrégés et non constitutifs d’une
validation indépendante ou d’une promesse de performance future.

## Construction

    PYTHONPATH=src python tools/package_public_quantitative_aggregates.py build \
      --input /path/to/sanitized-aggregate.json \
      --output-dir artifacts/candidates/v0.3.0/quantitative_aggregates

## Vérification

    PYTHONPATH=src python tools/package_public_quantitative_aggregates.py verify \
      --output-dir artifacts/candidates/v0.3.0/quantitative_aggregates

## Statut quantitatif du paquet

Le paquet candidat couvre 16 sections quantitatives et comporte
19 fichiers contrôlés, incluant les métadonnées, le manifest et
`SHA256SUMS`.

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
techniques de niveau institutionnel, reproductible, attesté, signé et
adapté à une due diligence, un sandbox ou un pilote contrôlé.

Les résultats sont rétrospectifs et ne constituent pas une promesse de
performance future. La significativité statistique est
benchmark-spécifique et n’est pas démontrée contre l’ensemble des
benchmarks.
