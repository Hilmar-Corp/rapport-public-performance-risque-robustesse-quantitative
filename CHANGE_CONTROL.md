# Politique de maîtrise des changements

## Modifications non matérielles

Les corrections documentaires, le formatage et les refactorisations non fonctionnelles exigent :

- la réussite de l’intégration continue ;
- un audit de la frontière de publication ;
- une revue du diff indexé.

## Modifications matérielles des stratégies de référence

Toute modification portant sur l’un des éléments suivants impose une nouvelle publication versionnée :

- la convention de coûts de transaction ;
- le décalage d’exécution ;
- les bornes d’exposition ;
- la formule d’annualisation ou de CAGR ;
- les paramètres des stratégies de référence ;
- la spécification du HMM ;
- la reconstruction des données d’entrée ;
- les schémas de publication ;
- les résultats de performance.

## Modifications de la frontière propriétaire

Toute modification affectant le niveau de divulgation de Nostra exige une revue explicite des éléments suivants :

- exposition du code du modèle ;
- caractéristiques et paramètres ;
- probabilités ;
- positions et rendements ;
- rotation et coûts ;
- publication de la courbe de valeur liquidative quotidienne ;
- chemins privés et infrastructure ;
- périmètre contractuel et régime de licence.

## Contrôles du dépôt

La branche par défaut doit rester protégée contre les poussées forcées et la suppression.
Les contrôles de statut doivent être validés avant l’acceptation de toute modification contrôlée.
