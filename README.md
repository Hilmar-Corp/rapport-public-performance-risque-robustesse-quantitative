# Rapport public de performance, de risque et de robustesse quantitative de Nostra AI

Ce dépôt fournit des outils Python transparents permettant d’évaluer des stratégies quotidiennes d’allocation, avec un décalage d’exécution explicite et une comptabilisation des coûts de transaction.

Il contient l’infrastructure publique d’évaluation et de validation, les stratégies publiques de référence ainsi que les artefacts assainis associés. Il ne contient aucune logique propriétaire du modèle, aucun jeu de données privé, aucune configuration de production, aucun signal historique, aucune trace de positions et aucun artefact interne de recherche.

## Stratégies de référence incluses

- Achat-conservation
- Allocation constante de 50 %
- Momentum en série temporelle sur 90 jours
- Croisement de moyennes mobiles 50/200 jours
- Ciblage de volatilité sur 30 jours
- HMM gaussien à trois états évalué en marche en avant

## Convention fondamentale

Une stratégie dynamique calcule sa décision à partir des informations disponibles jusqu’à la date t. Cette décision est décalée d’une observation quotidienne avant d’être appliquée aux rendements.

Les coûts de transaction sont imputés sur les variations absolues de la position appliquée, y compris lors du mouvement initial depuis une position en liquidités.

## Installation

    python -m pip install -e ".[dev,hmm]"

## Test synthétique de bon fonctionnement

    PYTHONPATH=src python examples/run_synthetic_example.py

L’exemple synthétique vérifie que chaque chemin d’exécution fonctionne et que les identités comptables sont respectées. Ses résultats numériques n’ont aucune signification empirique, comparative ou relative à la performance.

## Coûts d’exécution et capacité

Le package fournit également un moteur générique et calibrable séparant
frais, demi-spread, slippage et impact de marché. Il permet de construire des
surfaces synthétiques selon le notionnel, le volume, la volatilité et le taux
de participation, ainsi que d’estimer un break-even économique.

Ces calculs ne constituent pas une estimation de la capacité réelle de
Nostra AI. Voir `docs/EXECUTION_COST_AND_CAPACITY.md`.

## Contrôles

    PYTHONPATH=src python -m pytest
    python tools/audit_public_repository.py
    python -m ruff check .
    python -m ruff format --check .

## Périmètre

Ce dépôt contient une infrastructure d’évaluation et de validation. Il ne reproduit aucun modèle propriétaire de HilmarCorp et ne constitue pas un conseil en investissement.

## Reproductibilité et frontière propriétaire

Les stratégies publiques de référence sont reproductibles à partir de ce dépôt.

Nostra AI n’est pas publiée en open source. Ses caractéristiques, paramètres, probabilités et séries de positions restent propriétaires.

Les publications publiques distinguent :

- les références publiques classées `code-reproducible` ;
- les résultats agrégés de Nostra classés `artifact-verified`.

Voir `METHODOLOGY.md`, `REPRODUCIBILITY.md` et `PROPRIETARY_BOUNDARY.md`.

## Architecture finale de publication

Le dépôt public contient le cadre d’évaluation et les stratégies reproductibles de référence. Il ne contient ni le modèle Nostra, ni sa trace d’exécution, ni aucune série temporelle de Nostra.

Les métriques agrégées de Nostra sont vérifiées au moyen d’un engagement SHA-256 portant sur un artefact privé.

Un artefact séparé destiné au site internet peut afficher des observations quotidiennes de valeur liquidative avec un délai minimal de quatorze jours. Cet artefact n’est pas distribué dans ce dépôt et ne contient aucune position, aucun rendement quotidien explicite, aucune rotation, aucun coût, aucune probabilité et aucune caractéristique du modèle.

Voir `FINAL_PUBLICATION_ARCHITECTURE.md`.

## Matrice de validation quantitative

Le dépôt publie une matrice de 28 contrôles couvrant notamment le backtest,
l’absence de look-ahead, le risque de surajustement, la non-stationnarité,
les régimes, les coûts d’exécution, les risques de queue, la sensibilité,
la résilience des données et le monitoring.

Les fichiers de référence sont :

- `governance/quantitative_validation_control_matrix.csv` ;
- `governance/quantitative_evidence_commitments.csv` ;
- `docs/QUANTITATIVE_VALIDATION_ROADMAP.md`.

La matrice distingue le code public, les résultats publics, les preuves
privées engagées par SHA-256 et les conditions formelles de réouverture.
Les engagements cryptographiques ne publient aucun chemin privé, aucune
trace quotidienne, aucune caractéristique, aucun coefficient et aucun
seuil propriétaire. Ils ne constituent pas une validation indépendante.

## Reproductibilité institutionnelle

Les stratégies publiques de référence peuvent être réexécutées depuis un clone propre au moyen de la commande suivante :

    make reproduce

L’environnement contrôlé de dépendances Python 3.13 est consigné dans :

`requirements/constraints-py313.txt`

Les stratégies publiques de référence utilisent une exposition comprise entre 0 % et 100 %. L’évaluation propriétaire de Nostra utilise une plage gouvernée comprise entre -10 % et +100 %.

Les publications formelles comprennent des artefacts versionnés, des manifestes SHA-256, un audit des dépendances, une nomenclature CycloneDX des composants logiciels et des preuves produites par GitHub Actions.

Voir `DATA_PROVENANCE.md`, `RELEASE_POLICY.md`, `CHANGE_CONTROL.md` et `SUPPLY_CHAIN_SECURITY.md`.

## Régime de licence

Le code source du logiciel, les tests et la documentation technique sont placés sous licence Apache-2.0.

Les fichiers de performance contrôlés situés dans `artifacts/latest` ne sont pas placés sous licence Apache-2.0. Ils restent © HilmarCorp, tous droits réservés, et sont publiés uniquement à des fins d’inspection et de vérification.

La logique du modèle Nostra AI et sa trace privée d’exécution ne sont pas incluses dans ce dépôt. Voir `NOTICE` et `artifacts/LICENSE.md`.


## Reproduction OCI institutionnelle

L’environnement canonique peut être construit et exécuté dans une image OCI
référencée par digest :

~~~text
docker build --platform linux/amd64 -t hilmarbench-reproduction .
docker run --platform linux/amd64 --rm hilmarbench-reproduction
~~~

Chaque tag produit également une image GHCR, des SBOM CycloneDX et SPDX, un
manifeste de provenance et des attestations GitHub OIDC.

Voir `docs/RELEASE_EVIDENCE.md`.

## Paquet quantitatif agrégé figé v0.3.0

Le répertoire
`artifacts/candidates/v0.3.0/quantitative_aggregates`
constitue le paquet final contrôlé des résultats quantitatifs publics agrégés.

Il contient 21 sections vérifiées :

- stationnarité et dérive de distribution ;
- régimes de marché ;
- stress de coûts et de délais d’exécution ;
- placebo et risque de queue ;
- Monte Carlo historique et résilience des données ;
- sensibilité et ablation ;
- monitoring en shadow live ;
- Probabilistic Sharpe Ratio et Deflated Sharpe Ratio ;
- White Reality Check et Hansen SPA ;
- CSCV et Probability of Backtest Overfitting ;
- moving-block bootstrap de la surperformance composée.

- backtesting formel de la VaR et de l’Expected Shortfall ;
- analyse du Sharpe sous dépendance temporelle ;
- reverse stress historique des épisodes de perte réalisés ;
- reverse stress contrefactuel du modèle, du réentraînement et de la chaîne directionnelle.
- analyse de la profondeur, de la durée, de la récupération et du temps sous le précédent plus-haut des drawdowns.

Les différentiels de CAGR sont positifs contre les 11 benchmarks publics.
La significativité individuelle au seuil de 5 % est établie pour
2 comparaisons sur 11. Cette distinction ne doit pas être interprétée
comme une significativité universelle.

Nostra AI fonctionne en shadow live sur données réelles et sur
l’infrastructure de production. Ce dispositif constitue une validation
interne de production en conditions réelles. Il reste distinct d’un
déploiement contractuel chez un client et d’une validation externe
indépendante.

Le paquet est rétrospectif, artifact-verified, reproductible et soumis à
une frontière propriétaire stricte. Il ne publie aucune série journalière
Nostra, aucun réglage propriétaire ni aucune matrice privée de candidats.

Vérification :

    PYTHONPATH=src python tools/package_public_quantitative_aggregates.py verify \
      --output-dir artifacts/candidates/v0.3.0/quantitative_aggregates
