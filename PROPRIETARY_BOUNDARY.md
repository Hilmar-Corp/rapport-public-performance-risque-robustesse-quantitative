# Politique de frontière de propriété intellectuelle et de publication

## Objet

La présente politique définit la séparation entre :

- les éléments pouvant être publiés dans le dépôt public ;
- les résultats pouvant être communiqués uniquement sous forme agrégée ;
- les preuves privées conservées à des fins de contrôle et de réconciliation ;
- les éléments de production soumis à un accès strictement restreint.

Cette frontière vise simultanément :

1. la protection de la propriété intellectuelle de HilmarCorp ;
2. l’inspectabilité des méthodes publiques ;
3. l’intégrité des preuves quantitatives ;
4. la limitation du risque de reconstruction du modèle ;
5. la cohérence entre les publications, les releases et les preuves privées.

## Classification de l’information

| Classe | Définition | Exemples | Publication |
|---|---|---|---|
| `PUBLIC-REPRODUCIBLE` | Élément pouvant être recalculé à partir du dépôt public | Benchmarks, code générique, tests, conventions | Autorisée |
| `PUBLIC-AGGREGATE` | Résultat agrégé ne permettant pas de reconstruire le modèle ou sa trajectoire | Métriques agrégées, résultats de stress, conclusions statistiques | Autorisée sous contrôle |
| `PRIVATE-CONTROLLED` | Preuve privée conservée pour réconciliation, audit interne ou due diligence contrôlée | Artefacts d’évaluation, manifestes privés, résultats détaillés | Interdite sur GitHub |
| `RESTRICTED-PRODUCTION` | Élément opérationnel sensible ou secret | Identifiants, secrets, configuration de production, modèles sérialisés | Strictement interdite |

## Éléments autorisés à la publication

Le dépôt public peut contenir :

- le code source générique des stratégies publiques de référence ;
- les bibliothèques génériques de backtest, de risque et de validation ;
- les tests unitaires, contractuels, numériques et de propriété ;
- les conventions économiques et comptables ;
- les métriques agrégées autorisées de Nostra AI ;
- les résultats agrégés de robustesse, de stress et de sensibilité ;
- les limites méthodologiques et conclusions défavorables ;
- les manifestes publics ;
- les empreintes et engagements SHA-256 ;
- les SBOM, attestations de provenance et preuves de release ;
- les procédures publiques de reproduction et de vérification.

## Éléments interdits à la publication

Le dépôt public exclut notamment :

- la logique du modèle Nostra AI ;
- les caractéristiques, variables et transformations propriétaires ;
- les pondérations, paramètres, coefficients et seuils ;
- les probabilités et scores internes ;
- les matrices privées de candidats ou d’expérimentations ;
- les positions, expositions et signaux quotidiens ;
- les rendements quotidiens de Nostra AI ;
- les séries quotidiennes de valeur liquidative ou de drawdown ;
- les traces détaillées de rotation et de coûts ;
- les configurations de réentraînement ;
- les modèles sérialisés ;
- les données privées ou sous licence ;
- les identifiants de fournisseurs ;
- les chemins privés vers les sources ou artefacts ;
- les secrets, clés, jetons et identifiants d’accès ;
- l’architecture détaillée de production ;
- les traces internes de recherche ;
- les artefacts destinés au site internet lorsqu’ils permettent une
  reconstruction de la trajectoire privée.

Aucune série temporelle quotidienne de Nostra AI n’est distribuée dans ce
dépôt GitHub.

## Engagements cryptographiques

Les engagements SHA-256 permettent :

- de figer l’existence et l’intégrité d’une preuve privée ;
- de détecter toute modification ultérieure ;
- de réconcilier une publication publique avec une preuve conservée ;
- de conduire une revue contrôlée sans publier le contenu sous-jacent.

Un engagement cryptographique :

- ne rend pas la preuve privée publiquement reproductible ;
- ne constitue pas une validation indépendante ;
- ne constitue pas une certification réglementaire ;
- ne doit contenir aucun chemin privé ni secret opérationnel.

## Contrôle préalable à la publication

Toute modification de la surface publique doit satisfaire les contrôles
suivants :

1. classification préalable de l’information ;
2. application du principe de divulgation minimale ;
3. absence de séries privées ou de paramètres reconstructibles ;
4. cohérence avec les manifestes et engagements cryptographiques ;
5. contrôle automatisé de la frontière propriétaire ;
6. revue des changements par pull request ;
7. validation des tests et audits de publication ;
8. conservation de l’historique Git et des éléments de preuve de release.

La publication d’un résultat agrégé ne doit pas permettre, seule ou combinée
à d’autres éléments publics, de reconstituer matériellement le fonctionnement
du modèle.

## Communication sous confidentialité

Une preuve classée `PRIVATE-CONTROLLED` peut être communiquée dans un cadre de
due diligence contrôlée uniquement lorsque :

- le besoin de communication est défini ;
- le destinataire est autorisé ;
- un engagement de confidentialité applicable est en place ;
- le périmètre est limité aux éléments nécessaires ;
- la communication est traçable ;
- aucun secret ou accès de production n’est transmis.

Les éléments classés `RESTRICTED-PRODUCTION` ne sont pas destinés à une
communication commerciale ou publique.

## Gestion des incidents de publication

Toute exposition involontaire d’un élément privé doit entraîner :

1. l’arrêt de la diffusion concernée ;
2. l’identification du contenu exposé ;
3. la révocation ou rotation des secrets lorsque nécessaire ;
4. l’évaluation de l’impact sur la propriété intellectuelle et la sécurité ;
5. la correction du dépôt et des artefacts distribués ;
6. la conservation d’une trace de décision ;
7. la réévaluation des contrôles ayant permis l’incident.

La suppression d’un fichier dans un commit ultérieur ne suffit pas à effacer
son historique. Toute remédiation doit tenir compte de l’historique Git et des
copies distribuées.

## Responsabilité des déclarations publiques

La protection de la propriété intellectuelle ne doit jamais être utilisée pour
présenter comme publiquement reproductible un résultat qui ne l’est pas.

La terminologie obligatoire est :

- `code-reproducible` pour les éléments recalculables depuis le dépôt ;
- `artifact-verified` pour les résultats Nostra vérifiés par artefacts ;
- `private-controlled` pour les preuves conservées hors du dépôt ;
- `independent validation` uniquement lorsqu’une validation réellement
  indépendante et formalisée a été réalisée.

## Documents associés

- `METHODOLOGY.md` ;
- `METHODOLOGICAL_INTEGRITY.md` ;
- `REPRODUCIBILITY.md` ;
- `FINAL_PUBLICATION_ARCHITECTURE.md` ;
- `DATA_PROVENANCE.md` ;
- `CHANGE_CONTROL.md` ;
- `SUPPLY_CHAIN_SECURITY.md`.
