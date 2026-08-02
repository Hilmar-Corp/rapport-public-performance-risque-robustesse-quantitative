# Politique de publication

Une publication contrôlée doit satisfaire l’ensemble des contrôles suivants :

1. le formatage et l’analyse statique réussissent ;
2. les tests unitaires, les tests de propriétés et les contrôles contre l’utilisation d’informations futures réussissent ;
3. la couverture tenant compte des branches reste supérieure ou égale à 90 % ;
4. l’audit de la surface publique du dépôt réussit ;
5. le manifeste de publication et les contrôles SHA-256 réussissent ;
6. la reproduction des stratégies publiques de référence réussit ;
7. l’audit des dépendances réussit ;
8. CodeQL s’exécute avec succès ;
9. aucune série temporelle de Nostra ni aucun champ privé d’exécution n’est distribué ;
10. les artefacts versionnés deviennent immuables après leur publication.

## Paquets de référence historiques

`artifacts/latest` désigne le paquet public de référence utilisé pour la
reproduction des stratégies publiques historiques.

Dans l’état publié de `v0.3.0`, ce répertoire reste identique à
`artifacts/releases/v0.2.1`. Il ne constitue pas un pointeur de statut vers
le paquet quantitatif agrégé `v0.3.0`.

Les publications historiques `v0.2.0` et `v0.2.1` sont conservées dans :

`artifacts/releases/<version>`

## Paquet quantitatif agrégé v0.3.0

Le paquet quantitatif agrégé de `v0.3.0` conserve son emplacement
historique :

`artifacts/candidates/v0.3.0/quantitative_aggregates`

Ce chemin est maintenu afin de préserver les manifestes, les sommes de
contrôle et les engagements déjà publiés. Le terme `candidates` contenu
dans le chemin ne qualifie plus le statut de la release.

La release GitHub `v0.3.0`, son tag, ses actifs, ses empreintes SHA-256,
ses preuves de provenance et les résultats de l’intégration continue
constituent le point officiel de distribution.

Le paquet agrégé est publiquement vérifiable à partir de son manifeste.
Il n’est pas publiquement reconstructible depuis les preuves privées
sous-jacentes.

## Identité de release

Une publication GitHub associe les artefacts contrôlés, les contraintes
de dépendances et les nomenclatures des composants logiciels à un commit
et à un tag Git déterminés.

Le tag de publication est signé lorsqu’une clé de signature du dépôt est
configurée. À défaut, un tag annoté est utilisé conjointement avec
l’identité immuable du commit, les sommes de contrôle SHA-256 et les
preuves produites par GitHub Actions.
