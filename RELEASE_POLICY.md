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

`artifacts/latest` représente la publication contrôlée courante.

Chaque publication formelle est également copiée dans :

`artifacts/releases/<version>`

Une publication GitHub associe l’artefact versionné, les contraintes de dépendances et la nomenclature des composants logiciels à un commit et à un tag Git déterminés.

Le tag de publication est signé lorsqu’une clé de signature du dépôt est configurée. À défaut, un tag annoté est utilisé conjointement avec l’identité immuable du commit, les sommes de contrôle SHA-256 et les preuves produites par GitHub Actions.
