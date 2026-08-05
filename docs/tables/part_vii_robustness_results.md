# Partie VII - Non-stationnarité et robustesse

## Tableau 7.1 - Diagnostics de stationnarité et de rupture

| Indicateur | Résultat |
|---|---:|
| Séries anonymisées testées | 8 |
| Rejets ADF de la racine unitaire au seuil de 5 % | 2 |
| Rejets KPSS de la stationnarité au seuil de 5 % | 7 |
| Diagnostics concordants de stationnarité | 1 |
| Diagnostics contradictoires | 1 |
| Candidats de rupture CUSUM | 8 |

## Tableau 7.2 - Dérive des distributions

| Indicateur | Fenêtres glissantes | Plis apprentissage-évaluation |
|---|---:|---:|
| Comparaisons | 136 | 136 |
| Rejets KS de l'égalité des distributions | 134 (98,53 %) | 131 (96,32 %) |
| PSI supérieur ou égal à 0,25 | 125 (91,91 %) | 130 (95,59 %) |
| Décalage standardisé absolu supérieur ou égal à 1 | 80 (58,82 %) | 37 (27,21 %) |

## Tableau 7.3 - Résultats par régime anonymisé

| Régime | Observations | Surperformance logarithmique annualisée | Sharpe Nostra | Sharpe bitcoin | Volatilité Nostra | Volatilité bitcoin | Perte maximale Nostra | Perte maximale bitcoin |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| regime_01 | 632 | 32,57 % | 1,224 | 0,152 | 26,04 % | 47,55 % | -22,11 % | -63,69 % |
| regime_02 | 966 | -7,50 % | 1,979 | 1,316 | 31,26 % | 65,09 % | -15,10 % | -49,39 % |
| regime_03 | 1 036 | 36,09 % | 0,929 | -0,026 | 27,54 % | 50,85 % | -31,63 % | -76,09 % |
| regime_04 | 1 232 | 21,48 % | 1,521 | 0,579 | 27,62 % | 58,57 % | -19,54 % | -70,56 % |
| regime_05 | 404 | 41,60 % | 0,529 | -0,264 | 29,76 % | 55,69 % | -24,01 % | -55,99 % |
| regime_06 | 629 | -23,34 % | 2,165 | 1,680 | 33,69 % | 67,40 % | -15,07 % | -46,34 % |
| regime_07 | 1 261 | 4,68 % | 1,739 | 1,030 | 30,11 % | 58,34 % | -18,22 % | -63,47 % |
| regime_08 | 337 | 22,07 % | 1,576 | 0,564 | 26,15 % | 60,54 % | -13,22 % | -37,24 % |
| regime_09 | 741 | 32,72 % | 0,970 | 0,129 | 28,16 % | 57,92 % | -19,54 % | -67,52 % |
| regime_10 | 770 | 4,78 % | 1,398 | 0,892 | 32,07 % | 57,61 % | -21,61 % | -43,15 % |

## Tableau 7.4 - Sensibilité anonymisée de configuration

| Mesure | Minimum | Quantile 5 % | Médiane | Quantile 95 % | Maximum |
|---|---:|---:|---:|---:|---:|
| Accord directionnel | 86,16 % | 88,64 % | 96,70 % | 100,00 % | 100,00 % |
| Similarité de Pearson | 69,91 % | 79,34 % | 96,54 % | 100,00 % | 100,00 % |
| Similarité de Spearman | 80,83 % | 82,29 % | 94,49 % | 100,00 % | 100,00 % |
| Erreur absolue moyenne de trajectoire | 0,000 | 0,000 | 0,010 | 0,035 | 0,071 |
| Erreur quadratique moyenne de trajectoire | 0,000 | 0,000 | 0,020 | 0,063 | 0,103 |

Configurations exécutées : 34. Configurations en échec : 0.

## Tableau 7.5 - Placebos et permutations

| Métrique | Valeur observée | Médiane des permutations | Valeur p empirique | Lecture |
|---|---:|---:|---:|---|
| CAGR | 52,45 % | 51,95 % | 1,20 % | Inférieur à 5 % |
| Capital final | 12,8636 | 12,6075 | 1,20 % | Inférieur à 5 % |
| Ratio de Sharpe | 1,5877 | 1,5792 | 3,79 % | Inférieur à 5 % |
| Ratio de Calmar | 2,4522 | 2,4451 | 37,13 % | Non inférieur à 5 % |

## Tableau 7.6 - Ablations anonymisées

| Indicateur | Résultat |
|---|---:|
| Ablations anonymisées recensées | 15 |
| Comparaisons appariées soumises au bootstrap | 14 |
| Intervalles à 95 % incluant zéro | 14 |
| Intervalles entièrement positifs | 0 |
| Intervalles entièrement négatifs | 0 |

### Variations économiques des ablations

| Métrique | Minimum | Médiane | Maximum |
|---|---:|---:|---:|
| Écart de CAGR | -0,0491 % | 0,0069 % | 0,1754 % |
| Écart de capital final | -0,0251 | 0,0035 | 0,0899 |
| Écart de perte maximale | -0,0180 % | 0,0132 % | 0,1531 % |
| Écart de Sharpe | -0,0009 | 0,0001 | 0,0041 |
| Écart de Sortino | -0,0029 | 0,0002 | 0,0085 |

## Tableau 7.7 - Résilience des données

| Paramètre | Résultat |
|---|---:|
| Scénarios hors référence | 23 |
| Familles de scénarios | 3 |
| Répétitions de rééchantillonnage | 300 |
| Longueur des blocs | 30 observations |
| Comparaison croisée entre fournisseurs achevée | Non |

### Variations des métriques sous perturbation des données

| Métrique | Minimum | Médiane | Maximum |
|---|---:|---:|---:|
| Écart de volatilité annualisée | -0,0263 % | -0,0008 % | 0,0072 % |
| Écart de CAGR | -0,5087 % | -0,0044 % | 0,0227 % |
| Écart de capital final | -0,2578 | -0,0023 | 0,0116 |
| Écart de perte maximale | -0,0338 % | 0,0000 % | 0,2481 % |
| Écart de couverture des prédictions | -145,0000 | 0,0000 | 0,0000 |
| Écart de Sharpe | -0,0103 | -0,0001 | 0,0004 |

## Tableau 7.8 - Conclusion consolidée de robustesse

| Dimension | Résultat contrôlé | Lecture autorisée |
|---|---|---|
| Stationnarité | Une seule série sur huit présente un diagnostic concordant de stationnarité ; sept rejets KPSS et huit candidats CUSUM | La stabilité statistique des séries ne peut pas être supposée |
| Dérive des distributions | 134 rejets KS sur 136 entre fenêtres et 131 sur 136 entre plis | La dérive est généralisée dans les comparaisons publiées |
| Régimes de marché | 8 régimes sur 10 avec surperformance logarithmique positive ; réduction du risque dans les dix régimes | La réduction du risque est plus uniforme que la surperformance |
| Sensibilité de configuration | 34 configurations exécutées, aucune défaillance, similarités médianes élevées | La trajectoire est généralement stable sans être parfaitement invariante |
| Placebos | CAGR, capital final et Sharpe sous le seuil de 5 % ; Calmar au-dessus | Résultat favorable pour trois métriques, non concluant pour le Calmar |
| Ablations | 14 intervalles appariés sur 14 incluent zéro | Aucun composant anonymisé n'est isolément décisif dans la preuve publiée |
| Résilience des données | 23 scénarios hors référence ; médianes des écarts généralement proches de zéro | Résilience interne descriptive, sans validation inter-fournisseurs |

## Limites obligatoires

- Les séries, régimes, configurations et ablations sont publiés sous une forme anonymisée.
- Les contrôles de configuration, d'ablation et de résilience des données constituent des preuves descriptives.
- La non-stationnarité et la dérive observées empêchent de supposer une distribution stable sur l'ensemble de la période.
- Aucune comparaison croisée entre plusieurs fournisseurs de données n'est déclarée achevée.
- Les résultats sont rétrospectifs et ne démontrent ni invariance future ni relation causale.

Conclusion contrôlée : les résultats soutiennent une robustesse historique favorable malgré une non-stationnarité et une dérive matérielles. Cette conclusion ne démontre ni stabilité future, ni invariance du modèle, ni absence de risque de régime.
