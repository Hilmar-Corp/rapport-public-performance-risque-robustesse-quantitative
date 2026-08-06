# Partie IX - Exécution, capacité et shadow

## Tableau 9.1

### Sensibilité historique sélectionnée aux coûts et aux délais

| Scénario | Coût | Délai | CAGR | Sharpe | Drawdown maximal | Equity finale |
|---|---:|---:|---:|---:|---:|---:|
| Référence historique | 25 bps | 0 jour(s) | 52,45 % | 1,59 | -21,39 % | 12,86 |
| Coût élevé | 100 bps | 0 jour(s) | 43,88 % | 1,39 | -23,47 % | 9,06 |
| Délai de deux jours | 25 bps | 2 jour(s) | 49,60 % | 1,53 | -23,44 % | 11,47 |
| Stress combiné | 100 bps | 2 jour(s) | 41,19 % | 1,33 | -25,47 % | 8,08 |

## Tableau 9.2

### Hypothèses du cadre générique synthétique

| Hypothèse | Valeur | Statut |
|---|---:|---|
| Frais | 2,00 bps | Illustratif |
| Demi-spread | 3,00 bps | Illustratif |
| Slippage central | 5,00 bps | Illustratif |
| Coefficient d'impact | 8,00 bps | Illustratif |
| Exposant d'impact | 0,50 | Forme racine carrée |
| Participation de référence | 1,00 % | Illustratif |
| Limite de participation | 10,00 % | Illustratif |
| Volume quotidien | 100 millions | Illustratif |

Le coût total synthétique est la somme des frais, du demi-spread, du slippage et de l'impact de marché. L'impact dépend du taux de participation et de la volatilité quotidienne.

## Tableau 9.3

### Notionnel synthétique sous volatilité quotidienne illustrative de 4 %

| Edge brut hypothétique | Notionnel maximal | Participation | Coût estimé | Contrainte active |
|---:|---:|---:|---:|---|
| 8 bps | 0,000 millions | 0,00 % | 10,00 bps | fixed_cost |
| 12 bps | 0,062 millions | 0,06 % | 12,00 bps | expected_edge |
| 18 bps | 1,000 millions | 1,00 % | 18,00 bps | expected_edge |
| 25 bps | 3,516 millions | 3,52 % | 25,00 bps | expected_edge |
| 50 bps | 10,000 millions | 10,00 % | 35,30 bps | participation_limit |
| 100 bps | 10,000 millions | 10,00 % | 35,30 bps | participation_limit |

Ces notionnels sont des sorties d'un exemple synthétique. Ils ne représentent ni Nostra AI, ni un client, ni un broker, ni un lieu d'exécution. Cette grille n'est pas une estimation de capacité réelle.

## Tableau 9.4

### Snapshot public du monitoring shadow

| Indicateur | Valeur |
|---|---:|
| Première observation | 2026-06-26 |
| Dernière observation | 2026-07-20 |
| Jours calendaires | 25 |
| Jours observés | 23 |
| Jours manquants | 2 |
| Couverture | 92 % |
| Collecte technique complète | Oui |
| Approbation humaine requise | Oui |
| Approbation pilote ou production limitée | Non |
| Décision de readiness production | not_made |

## Lecture consolidée

La grille historique indique que la performance demeure positive dans toutes les combinaisons publiques de coûts et de délais, mais qu'elle se dégrade à mesure que le coût ou le délai augmente. Le cadre générique d'exécution démontre une architecture méthodologique cohérente pour les frais, le spread, le slippage, l'impact et les contraintes de capacité. Il n'est pas calibré sur des exécutions réelles de Nostra AI ou d'un client.

Le monitoring shadow constitue une preuve opérationnelle interne limitée. Le snapshot public couvre 23 jours observés sur 25 jours calendaires et ne contient pas une série de performance permettant une outcome analysis complète. Il ne matérialise aucune approbation pilote ou production.

### Limites

- Les sensibilités coûts-délais sont historiques et ne constituent pas des devis d'exécution.
- Les hypothèses de slippage et d'impact utilisées dans la surface générique sont synthétiques.
- Aucune capacité réelle de Nostra AI ou d'un client n'est estimée.
- Aucune donnée d'ordre client, de broker ou de lieu d'exécution n'est utilisée.
- Le snapshot shadow public s'arrête au 20 juillet 2026 et ne couvre pas un mois complet.
- L'export shadow ne contient pas de série contrôlée de performance permettant une outcome analysis complète.
- Aucune décision publique de readiness, d'approbation pilote ou de production limitée n'a été prise.
- Les résultats ne constituent ni une validation externe indépendante, ni une prévision, ni une garantie.

Conclusion contrôlée : la robustesse historique aux coûts et aux délais est favorable dans la grille publique examinée. La capacité réelle, la qualité d'exécution client et l'équivalence entre historique et shadow ne sont pas démontrées.
