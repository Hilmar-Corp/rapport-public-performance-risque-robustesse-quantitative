# Provenance des données publiques de référence

## Donnée publique canonique

Le processus déterministe de reproduction publique ne dépend d’aucun point d’accès mutable à des données de marché en direct.

Il reproduit l’artefact public engagé et ses conventions de calcul. Il ne reconstruit pas une série brute indépendante depuis un fournisseur de données de marché et ne constitue pas une validation indépendante des données amont.

Il reconstruit la série canonique des rendements quotidiens du BTC à partir de la courbe engagée `buy_and_hold_equity` contenue dans :

`artifacts/latest/baseline_daily_curves.csv`

La première observation intègre le mouvement initial documenté depuis une position en liquidités ainsi que le coût de transaction de 25 points de base. Les observations suivantes sont reconstruites à partir des rapports successifs de la courbe de valeur liquidative de la stratégie d’achat-conservation.

Le fichier source est protégé par le manifeste de publication et par les sommes de contrôle SHA-256.

## Finalité

Ce processus permet de vérifier que :

- les courbes publiques publiées sont cohérentes entre elles ;
- le code source des stratégies de référence reproduit les résultats publics engagés ;
- le décalage d’exécution, la rotation, les coûts et les métriques sont appliqués de manière cohérente ;
- aucune modification future du code ou des dépendances ne peut altérer silencieusement la publication.

## Limite

La réexécution publique valide le calcul des stratégies de référence et la surface d’évaluation engagée. Elle ne constitue ni un audit indépendant du fournisseur amont de données de marché, ni un audit de la trace propriétaire d’évaluation de Nostra.
