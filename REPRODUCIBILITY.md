# Politique de reproductibilité et de vérification

## Objet

Ce document définit les niveaux de reproductibilité applicables aux éléments
publiés dans ce dépôt.

La reproductibilité est qualifiée selon la nature de la preuve disponible et
ne doit pas être présentée comme uniforme pour tous les composants.

## Niveaux de preuve

| Niveau | Définition | Application |
|---|---|---|
| `code-reproducible` | Le résultat peut être recalculé à partir du code, des données et des conventions publiques prévues | Stratégies publiques de référence |
| `artifact-verified` | Le résultat est vérifié à partir d’un artefact contrôlé, manifesté et engagé cryptographiquement | Résultats agrégés de Nostra AI |
| `private-controlled` | La preuve détaillée est conservée hors du dépôt et accessible uniquement dans un cadre contrôlé | Artefacts privés et traces détaillées |
| `independent validation` | Une partie suffisamment indépendante réalise une validation formelle | Non revendiquée par ce dépôt |

## Stratégies publiques de référence

Les stratégies publiques de référence sont reproductibles par le code.

Le dépôt fournit notamment :

- les conventions d’exposition ;
- les règles de décalage d’exécution ;
- les coûts de transaction ;
- les méthodes de calcul ;
- les tests comptables ;
- les données ou procédures publiques prévues ;
- les contraintes d’environnement ;
- les commandes de reproduction.

## Nostra AI

Nostra AI n’est pas publiée en open source.

Ses résultats publics sont classés `artifact-verified` parce que :

- les résultats agrégés sont produits depuis un artefact contrôlé ;
- le paquet public possède un manifeste déterministe ;
- les fichiers sont vérifiés par SHA-256 ;
- les engagements cryptographiques permettent une réconciliation ultérieure ;
- l’audit public vérifie l’absence de contenu propriétaire interdit.

Le dépôt ne publie pas :

- la logique du modèle ;
- les variables propriétaires ;
- les paramètres ;
- les signaux ;
- les positions ;
- les rendements quotidiens ;
- la trace d’exécution privée.

## Contrôles techniques

Le cadre applique notamment :

- des tests comptables déterministes ;
- des tests de décalage d’exécution ;
- des contrôles contre l’utilisation d’informations futures ;
- une couverture tenant compte des branches ;
- des manifestes de publication ;
- des vérifications SHA-256 ;
- un audit automatisé de la frontière de publication ;
- une reproduction sous environnement contraint ;
- des contrôles multi-versions Python ;
- une reproduction OCI ;
- des SBOM et attestations de provenance.

## Limites

Ce cadre :

- ne rend pas le modèle propriétaire publiquement reproductible ;
- ne constitue pas une validation externe indépendante ;
- ne constitue pas un audit externe ;
- ne constitue pas une certification réglementaire ;
- ne garantit pas la répétition future des résultats historiques.

Toute communication doit conserver la distinction entre
`code-reproducible`, `artifact-verified` et `independent validation`.
