# Architecture institutionnelle des preuves de release

## Objet

Chaque release formelle relie une version logicielle contrôlée, un
environnement reproductible, des preuves de chaîne logicielle et des artefacts
quantitatifs vérifiés.

## Éléments constitutifs

Une release formelle comprend ou référence :

- un commit Git identifié ;
- un tag de version ;
- une image Python de base référencée par digest ;
- une image OCI de reproduction publiée sur GHCR ;
- des contraintes exactes de dépendances Python ;
- une nomenclature CycloneDX ;
- une nomenclature SPDX ;
- des empreintes SHA-256 ;
- un manifeste de provenance ;
- des attestations GitHub OIDC ;
- des artefacts quantitatifs contrôlés ;
- les résultats des workflows GitHub Actions.

## Preuves de contrôle quantitatif

Le dépôt comprend une matrice publique couvrant 28 contrôles quantitatifs et
un registre séparé d’engagements SHA-256 vers les preuves privées réconciliées.

Les contrôles couvrent notamment :

- causalité et absence de look-ahead ;
- overfitting et data snooping ;
- PBO, bootstrap et corrections de tests multiples ;
- non-stationnarité, drift et régimes ;
- coûts, délais, slippage, impact et capacité ;
- VaR, Expected Shortfall et risques de queue ;
- Monte Carlo et reverse stress ;
- sensibilité, ablations et résilience des données ;
- drawdowns et dépendance temporelle ;
- monitoring, outcome analysis et gouvernance de publication.

## Frontière propriétaire

Le registre public ne contient :

- aucun chemin privé ;
- aucune variable du modèle ;
- aucun coefficient ;
- aucun seuil ;
- aucune position quotidienne ;
- aucun rendement quotidien ;
- aucune trace privée d’exécution ;
- aucun secret ou identifiant de production.

Les engagements permettent de contrôler l’intégrité et d’effectuer une
réconciliation ultérieure. Ils ne rendent pas les preuves privées
publiquement reproductibles.

## Niveau de preuve

Nostra AI reste classée `artifact-verified`.

La logique propriétaire du modèle et sa trace d’exécution ne sont pas incluses
dans le dépôt.

Le paquet peut soutenir :

- une due diligence ;
- une revue quantitative ;
- une évaluation en sandbox ;
- un pilote contrôlé ;
- une réconciliation de preuves privées.

Il ne constitue pas :

- une validation indépendante externe ;
- un audit externe ;
- une certification réglementaire ;
- une garantie de performance future ;
- une décision d’aptitude universelle à la production.

## Documents de référence

- `governance/quantitative_validation_control_matrix.csv` ;
- `governance/quantitative_evidence_commitments.csv` ;
- `docs/QUANTITATIVE_VALIDATION_ROADMAP.md` ;
- `docs/QUANTITATIVE_RESEARCH_FREEZE_V0.3.0.md` ;
- `PROPRIETARY_BOUNDARY.md` ;
- `METHODOLOGICAL_INTEGRITY.md` ;
- `REPRODUCIBILITY.md`.
