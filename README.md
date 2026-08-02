<div align="center">

# HilmarCorp — Nostra AI

## Preuves publiques de performance, de risque et de robustesse quantitative

Cadre public contrôlé d’évaluation, de validation et de reproductibilité
quantitative de Nostra AI.

<p>
  <a href="https://github.com/Hilmar-Corp/rapport-public-performance-risque-robustesse-quantitative/releases/tag/v0.3.0">
    <img alt="Release v0.3.0" src="https://img.shields.io/badge/release-v0.3.0-1f6feb">
  </a>
  <a href="https://github.com/Hilmar-Corp/rapport-public-performance-risque-robustesse-quantitative/actions/workflows/quality.yml">
    <img alt="Contrôles de qualité" src="https://github.com/Hilmar-Corp/rapport-public-performance-risque-robustesse-quantitative/actions/workflows/quality.yml/badge.svg?branch=main">
  </a>
  <img alt="308 tests" src="https://img.shields.io/badge/tests-308%20réussis-2ea043">
  <img alt="Couverture 100 %" src="https://img.shields.io/badge/couverture-100%25-2ea043">
  <img alt="Python 3.11 à 3.13" src="https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-3776AB">
  <img alt="Licence Apache 2.0" src="https://img.shields.io/badge/licence-Apache--2.0-blue">
</p>

**Version quantitative historique v0.3.0 figée**

[Vue d’ensemble](#vue-densemble) ·
[Périmètre](#périmètre-public) ·
[Architecture](#architecture-de-publication) ·
[Validation](#couverture-de-validation) ·
[Vérification](#vérification-et-reproduction) ·
[Documentation](#documentation-de-référence)

</div>

---

## Vue d’ensemble

Ce dépôt constitue la surface publique de preuve quantitative de Nostra AI.

Il permet d’inspecter les méthodes d’évaluation, les stratégies publiques de
référence, les contrôles statistiques, les résultats agrégés autorisés à la
publication et les mécanismes de réconciliation avec les preuves privées.

| Élément | Statut contrôlé |
|---|---:|
| Version publique | `v0.3.0` |
| Modèle évalué | Nostra AI V5.246 |
| Statut de recherche historique | Figé |
| Période d’évaluation | 14 mai 2020 au 2 juin 2026 |
| Observations quotidiennes | 2 211 |
| Stratégies publiques comparées | 11 |
| Contrôles quantitatifs | 28 |
| Sections publiques de preuve | 21 |
| Tests automatisés | 308 |
| Instructions couvertes | 1 978 / 1 978 |
| Branches couvertes | 892 / 892 |
| Couverture totale | 100 % |
| Audit de publication | Réussi |
| Reproduction de référence | Réussie |

La campagne historique ne peut être rouverte qu’en présence :

1. d’un défaut matériel de données ;
2. d’un défaut matériel d’implémentation ;
3. d’un changement de modèle approuvé par la gouvernance ;
4. de nouvelles preuves live ou pilote nécessitant une outcome analysis formelle.

## Périmètre public

### Ce que le dépôt publie

- le code générique de backtest, de risque et de validation ;
- les stratégies publiques de référence ;
- les méthodes statistiques génériques ;
- les résultats agrégés assainis relatifs à Nostra AI ;
- les manifestes et engagements SHA-256 ;
- les tests, audits et procédures de reproduction ;
- les limites méthodologiques et les conclusions défavorables ;
- les preuves techniques de release et de provenance.

### Ce que le dépôt ne publie pas

- la logique propriétaire du modèle Nostra AI ;
- les variables, transformations et paramètres internes ;
- les coefficients et seuils propriétaires ;
- les signaux, positions ou expositions quotidiennes ;
- les rendements quotidiens de Nostra AI ;
- les données privées ou configurations de production ;
- les artefacts internes de recherche ;
- les identifiants de fournisseurs privés.

| Catégorie | Niveau de vérification |
|---|---|
| Stratégies publiques de référence | `code-reproducible` |
| Résultats agrégés de Nostra AI | `artifact-verified` |
| Preuves détaillées de Nostra AI | Privées, engagées par SHA-256 |

## Architecture de publication

La publication repose sur deux chaînes distinctes qui convergent vers un
paquet public unique, versionné et auditable.

### Chaîne publique reproductible

| Étape | Fonction | Vérification |
|---|---|---|
| Données de marché publiques | Entrées communes et inspectables | Publique |
| Stratégies de référence | Benchmarks recalculables | Code reproductible |
| Cadre de backtest et de risque | Conventions homogènes d’évaluation | Testé |
| Résultats publics | Résultats recalculables depuis le dépôt | Code reproductible |

### Chaîne de preuve Nostra AI

| Étape | Fonction | Publication |
|---|---|---|
| Artefact privé Nostra AI | Source propriétaire de l’évaluation | Privée |
| Résultats agrégés assainis | Indicateurs autorisés à la publication | Publique agrégée |
| Engagements SHA-256 | Réconciliation avec les preuves privées | Publique |
| Paquet public contrôlé | Ensemble versionné et manifesté | Publique |
| Audit de publication | Contrôle d’intégrité et de frontière propriétaire | Automatisé |
| Release GitHub v0.3.0 | Point officiel de distribution | Publique |

### Flux de contrôle

| Origine | Traitement | Destination |
|---|---|---|
| Données publiques | Benchmarks et cadre commun | Résultats reproductibles |
| Artefact privé Nostra AI | Assainissement et agrégation | Résultats publics Nostra |
| Preuves privées | Calcul des engagements SHA-256 | Registre public |
| Résultats et engagements | Packaging, manifeste et audit | Release GitHub v0.3.0 |

Cette architecture expose une preuve quantitative inspectable sans publier la
propriété intellectuelle du modèle.

## Stratégies publiques de référence

| Stratégie | Description |
|---|---|
| Achat-conservation | Exposition passive continue |
| Allocation constante de 50 % | Exposition statique intermédiaire |
| Momentum 90 jours | Momentum en série temporelle |
| Moyennes mobiles 50/200 | Croisement de tendances |
| Ciblage de volatilité 30 jours | Exposition ajustée au risque |
| HMM gaussien à trois états | Régimes estimés en marche en avant |

Une stratégie dynamique calcule sa décision avec les informations disponibles
jusqu’à la date `t`. La décision est décalée d’une observation quotidienne
avant d’être appliquée aux rendements.

Les coûts sont imputés sur les variations absolues de l’exposition appliquée,
y compris lors du mouvement initial depuis une position en liquidités.

## Couverture de validation

### Construction et exécution du backtest

- causalité et absence de fuite d’information future ;
- décalage explicite des décisions dynamiques ;
- contrôles d’intégrité comptable ;
- frais, demi-spread, slippage et impact de marché ;
- rotation, participation, capacité et break-even économique ;
- stress de coûts et de délais ;
- tests placebo.

### Robustesse statistique

- Probabilistic Sharpe Ratio ;
- Deflated Sharpe Ratio ;
- White Reality Check ;
- Hansen Superior Predictive Ability ;
- Combinatorially Symmetric Cross-Validation ;
- Probability of Backtest Overfitting ;
- moving-block bootstrap ;
- dépendance temporelle du Sharpe ;
- stationnarité et dérive de distribution ;
- régimes de marché ;
- sensibilité et ablations ;
- résilience des données.

### Risque et scénarios défavorables

- volatilité et drawdown ;
- Value at Risk et Expected Shortfall ;
- backtesting formel de la VaR et de l’Expected Shortfall ;
- risques de queue ;
- Monte Carlo historique ;
- reverse stress historique ;
- reverse stress contrefactuel ;
- profondeur des drawdowns ;
- durée et récupération ;
- temps sous le précédent plus-haut.

### Gouvernance et chaîne logicielle

- matrice publique de 28 contrôles ;
- registre d’engagements cryptographiques ;
- manifestes déterministes ;
- contrôle automatisé de la frontière propriétaire ;
- tests sous Python 3.11, 3.12 et 3.13 ;
- reproduction OCI ;
- SBOM CycloneDX et SPDX ;
- provenance GitHub OIDC ;
- CodeQL ;
- contrôle des dépendances ;
- sauvegarde et restauration du dépôt.

## Intégrité méthodologique et frontière de propriété intellectuelle

| Principe | Application institutionnelle |
|---|---|
| Divulgation minimale | Publication limitée aux informations nécessaires à l’inspection |
| Qualification des preuves | Distinction entre `code-reproducible`, `artifact-verified` et preuve privée |
| Présentation symétrique | Conservation des limites et résultats défavorables |
| Prudence statistique | Aucune généralisation au-delà des tests disponibles |
| Traçabilité | Méthodes, changements, manifestes et releases versionnés |
| Protection de l’IP | Aucune série, variable, configuration ou trace privée reconstructible |
| Correction | Toute erreur matérielle doit être corrigée, même si elle dégrade une conclusion |
| Indépendance | Aucune validation indépendante n’est revendiquée sans preuve correspondante |

La frontière de propriété intellectuelle est définie dans
[`PROPRIETARY_BOUNDARY.md`](PROPRIETARY_BOUNDARY.md).

Les règles de présentation, d’interprétation et de correction sont définies
dans
[`METHODOLOGICAL_INTEGRITY.md`](METHODOLOGICAL_INTEGRITY.md).

## Lecture des résultats

Les différentiels historiques de CAGR publiés sont positifs contre les
11 stratégies publiques de référence.

Deux comparaisons sur onze sont individuellement significatives au seuil de
5 %. Les résultats ne sont donc pas présentés comme universellement
significatifs.

Le shadow live constitue une validation interne sur données réelles et
infrastructure de production. Il reste distinct d’un déploiement contractuel
chez un client et d’une validation externe indépendante.

Les résultats sont historiques. Ils ne constituent ni une garantie, ni une
prévision de performance future, ni un conseil en investissement.

## Paquet quantitatif public v0.3.0

Le paquet contrôlé est conservé dans :

    artifacts/candidates/v0.3.0/quantitative_aggregates

Il comprend 21 sections publiques agrégées, leurs métadonnées, leur manifeste
et leurs empreintes SHA-256.

Le nom historique `candidates` est conservé afin de préserver l’intégrité des
manifestes et engagements déjà publiés. La release GitHub `v0.3.0` constitue
le point officiel de distribution.

## Vérification et reproduction

### Installation

    python -m pip install -e ".[dev,hmm]"

### Contrôles locaux

    python -m ruff check .
    python -m ruff format --check .
    PYTHONPATH=src python -m pytest
    PYTHONPATH=src python tools/audit_public_repository.py

### Vérification du paquet public

    PYTHONPATH=src python \
      tools/package_public_quantitative_aggregates.py \
      verify \
      --output-dir artifacts/candidates/v0.3.0/quantitative_aggregates

### Reproduction de référence

    make reproduce

### Reproduction OCI

    docker build \
      --platform linux/amd64 \
      -t hilmarbench-reproduction .

    docker run \
      --platform linux/amd64 \
      --rm \
      hilmarbench-reproduction

L’environnement Python 3.13 contrôlé est consigné dans :

    requirements/constraints-py313.txt

## Organisation du dépôt

| Répertoire | Fonction |
|---|---|
| `.github/workflows/` | Qualité, sécurité, reproduction et publication |
| `artifacts/` | Releases et preuves publiques contrôlées |
| `docs/` | Documentation quantitative et gouvernance |
| `governance/` | Matrice de contrôle et engagements de preuves |
| `requirements/` | Contraintes d’environnement reproductible |
| `src/hilmarbench/` | Code public générique de validation |
| `tests/` | Tests unitaires, contractuels et de couverture |
| `tools/` | Audit, packaging, reproduction et publication |
| `examples/` | Exemples synthétiques sans portée empirique |

## Documentation de référence

| Document | Objet |
|---|---|
| [`METHODOLOGY.md`](METHODOLOGY.md) | Conventions quantitatives générales |
| [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) | Niveaux de reproductibilité et de vérification |
| [`PROPRIETARY_BOUNDARY.md`](PROPRIETARY_BOUNDARY.md) | Politique de classification, de divulgation et de protection de l’IP |
| [`METHODOLOGICAL_INTEGRITY.md`](METHODOLOGICAL_INTEGRITY.md) | Standard d’intégrité et d’honnêteté méthodologique |
| [`FINAL_PUBLICATION_ARCHITECTURE.md`](FINAL_PUBLICATION_ARCHITECTURE.md) | Architecture de publication |
| [`DATA_PROVENANCE.md`](DATA_PROVENANCE.md) | Provenance et contrôle des données |
| [`RELEASE_POLICY.md`](RELEASE_POLICY.md) | Politique de version et de release |
| [`CHANGE_CONTROL.md`](CHANGE_CONTROL.md) | Gouvernance des changements |
| [`SUPPLY_CHAIN_SECURITY.md`](SUPPLY_CHAIN_SECURITY.md) | Sécurité de la chaîne logicielle |
| [`SECURITY.md`](SECURITY.md) | Politique de sécurité du dépôt |
| [`CHANGELOG.md`](CHANGELOG.md) | Historique des versions |
| [`docs/EXECUTION_COST_AND_CAPACITY.md`](docs/EXECUTION_COST_AND_CAPACITY.md) | Coûts et capacité |
| [`docs/COUNTERFACTUAL_REVERSE_STRESS.md`](docs/COUNTERFACTUAL_REVERSE_STRESS.md) | Reverse stress contrefactuel |
| [`docs/QUANTITATIVE_VALIDATION_ROADMAP.md`](docs/QUANTITATIVE_VALIDATION_ROADMAP.md) | Périmètre réconcilié |
| [`docs/QUANTITATIVE_RESEARCH_FREEZE_V0.3.0.md`](docs/QUANTITATIVE_RESEARCH_FREEZE_V0.3.0.md) | Décision de gel |
| [`docs/RELEASE_EVIDENCE.md`](docs/RELEASE_EVIDENCE.md) | Preuves techniques de release |

## Gouvernance quantitative

Les fichiers de référence sont :

- `governance/quantitative_validation_control_matrix.csv` ;
- `governance/quantitative_evidence_commitments.csv` ;
- `docs/QUANTITATIVE_VALIDATION_ROADMAP.md` ;
- `docs/QUANTITATIVE_RESEARCH_FREEZE_V0.3.0.md`.

Les engagements cryptographiques ne publient aucun chemin privé, aucune trace
quotidienne, aucune caractéristique, aucun coefficient et aucun seuil
propriétaire.

## Release officielle

La release contrôlée est disponible ici :

**[v0.3.0 — Gel de la recherche quantitative](https://github.com/Hilmar-Corp/rapport-public-performance-risque-robustesse-quantitative/releases/tag/v0.3.0)**

Elle comprend :

- le paquet de preuves quantitatives agrégées ;
- son archive versionnée ;
- son fichier d’empreinte SHA-256 ;
- les notes formelles de gel de la campagne historique.

## Limites

Ce dépôt :

- ne constitue pas une validation indépendante du modèle ;
- ne constitue pas une certification réglementaire ;
- ne fournit pas une estimation contractuelle de capacité d’exécution ;
- ne contient pas la chaîne privée de production de Nostra AI ;
- ne constitue pas un conseil en investissement ;
- ne garantit aucune performance future.

## Licence et droits

Le code public, les tests et la documentation technique sont placés sous
licence Apache-2.0.

Les artefacts de performance contrôlés restent © HilmarCorp, tous droits
réservés, et sont publiés exclusivement à des fins d’inspection et de
vérification.

La logique, les variables, les paramètres et la trace d’exécution de Nostra AI
ne sont pas inclus dans ce dépôt.
