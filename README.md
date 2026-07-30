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
