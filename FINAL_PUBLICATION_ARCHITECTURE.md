# Architecture finale de publication

## Dépôt GitHub

Le dépôt GitHub public contient :

- le moteur d’évaluation et de comptabilisation ;
- les stratégies publiques de référence ;
- les tests et contrôles contre l’utilisation d’informations futures ;
- les métriques agrégées de performance ;
- les courbes quotidiennes des références publiques ;
- les artefacts contrôlés et versionnés ;
- les manifestes cryptographiques ;
- les contraintes de dépendances et la documentation de gouvernance.

Les stratégies publiques de référence sont reproductibles par le code et vérifiables par réexécution.

Nostra AI est vérifiée au moyen d’artefacts et n’est pas publiée en open source.

Le dépôt GitHub ne contient aucune série temporelle ni aucune trace d’exécution de Nostra.

## Conventions d’exposition

Les stratégies publiques de référence utilisent une exposition comprise entre 0 % et 100 %.

L’évaluation propriétaire de Nostra utilise une plage d’exposition gouvernée comprise entre -10 % et +100 %.

## Site internet de HilmarCorp

Le site internet peut afficher les courbes quotidiennes de valeur liquidative de Nostra et des stratégies de référence au moyen d’un artefact généré séparément.

Cet artefact applique un délai minimal de publication de quatorze jours et contient uniquement des observations de valeur liquidative. Il ne contient aucune position, aucun rendement quotidien explicite, aucune rotation, aucun coût de transaction, aucune probabilité et aucune caractéristique du modèle.

## Environnement privé

L’environnement privé conserve la trace complète d’évaluation de Nostra, la logique du modèle, les positions, les rendements, les coûts, la rotation, les données de recherche et les preuves relatives aux sources amont.

## Convention de performance

Le CAGR est calculé selon la formule suivante :

`final_equity ** (365 / observations) - 1`
