# Modèle public de coûts d’exécution et de capacité

## Objet

Le module `hilmarbench.execution` fournit un cadre générique et calibrable
pour analyser les coûts d’exécution, l’impact de marché et la capacité
économique d’une stratégie d’allocation.

Il ne constitue pas une estimation de la capacité réelle de Nostra AI. Il
n’utilise aucune donnée de client, de broker, de lieu d’exécution ni aucune
trace propriétaire de Nostra.

## Décomposition des coûts

Pour un ordre non nul, le coût total en points de base est défini par :

    coût total
    = frais
    + demi-spread
    + slippage
    + impact de marché

L’impact de marché suit une loi de puissance configurable :

    impact
    = coefficient d’impact
    x (participation / participation de référence) ^ exposant
    x (volatilité / volatilité de référence)

L’exposant par défaut est `0,5`, correspondant à une forme racine carrée.

Le taux de participation est :

    participation
    = notionnel de l’ordre / volume quotidien négocié

Le coût monétaire est :

    coût monétaire
    = notionnel de l’ordre
    x coût total en bps
    / 10 000

## Intégration au backtest

Le mode historique de `run_backtest` conserve la convention fixe
`BacktestConfig.cost_bps`.

Le mode avancé utilise `ExecutionModelInputs` et calcule, pour chaque
variation absolue de position :

- le notionnel de l’ordre ;
- le taux de participation ;
- les frais ;
- le demi-spread ;
- le slippage ;
- l’impact ;
- le coût total ;
- le respect de la limite de participation.

Les deux modes sont mutuellement exclusifs afin d’éviter le double comptage.

## Capacité et break-even

La fonction `estimate_capacity_from_edge` recherche le notionnel maximal
compatible avec :

- l’edge brut attendu ;
- les coûts fixes ;
- l’impact de marché ;
- la limite maximale de participation.

Trois contraintes peuvent être actives :

- `fixed_cost` : l’edge ne couvre pas les coûts fixes ;
- `expected_edge` : l’impact consomme entièrement l’edge disponible ;
- `participation_limit` : la limite de participation est atteinte avant le
  break-even économique.

## Surface synthétique

La fonction `build_execution_scenario_surface` produit une grille
déterministe selon :

- le notionnel ;
- le volume quotidien ;
- la volatilité ;
- le slippage.

Commande d’exécution :

    PYTHONPATH=src python examples/run_execution_capacity_example.py

Les hypothèses de cet exemple sont exclusivement synthétiques. Les résultats
ne doivent pas être présentés comme une capacité réelle, un devis
d’exécution, une prévision ou une validation indépendante.

## Calibration réelle

Une utilisation économique nécessite notamment :

- des frais contractuels ;
- un spread observé ;
- une distribution de slippage ;
- une définition du volume pertinent ;
- une calibration du coefficient et de l’exposant d’impact ;
- une segmentation par broker, lieu, heure et régime de liquidité ;
- une politique de participation ;
- des données d’ordres et d’exécutions suffisamment longues.

Sans ces éléments, le module démontre la cohérence méthodologique du cadre,
pas la capacité réelle d’un produit ou d’un client.
