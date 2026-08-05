# Résultats statistiques institutionnels de la Partie VI

Source contrôlée : six agrégats publics artifact-verified de la release v0.3.0.

## Tableau 6.1 - Probabilistic Sharpe Ratio et Deflated Sharpe Ratio

| Mesure | PSR | DSR |
|---|---:|---:|
| Observations | 2211 | 2211 |
| Annualisation | 365 | 365 |
| Sharpe observé | 1,5877 | n/a |
| Maximum de Sharpe attendu | n/a | 0,002106 |
| Nombre d'essais | n/a | 15 |
| Skewness | 0,6847 | 0,6847 |
| Kurtosis de Pearson | 9,3507 | 9,3507 |
| Statistique de test | 3,9925 | 3,9872 |
| Probabilité | 99,9967 % | 99,9967 % |
| Statut méthodologique | `accepted_with_disclosed_limitation` | `accepted_with_disclosed_limitation` |

Le PSR corrige la non-normalité empirique mais ne corrige pas explicitement la dépendance sérielle. Le DSR repose sur quinze essais agrégés ; la matrice sous-jacente n'est pas publiée.

## Tableau 6.2 - White Reality Check et Hansen SPA

| Test | P-value publiée | Qualification |
|---|---:|---|
| White Reality Check | 0,0000 %* | `requalified_non_studentized_test` |
| Hansen SPA | 0,0000 %* | `accepted_with_disclosed_limitation` |

- Référence nulle : `zero daily return`
- Candidats : 15
- Répétitions : 2000
- Taille de bloc : 21

\* Les valeurs nulles publiées sont bornées par la résolution de la procédure de rééchantillonnage finie et ne constituent pas des zéros mathématiques.

## Tableau 6.3 - CSCV et Probability of Backtest Overfitting

| Mesure | Valeur |
|---|---:|
| Blocs CSCV | 8 |
| Candidats | 15 |
| Combinaisons par configuration | 70 |
| Configurations testées | 4 |
| PBO minimum | 10,00 % |
| PBO médian | 15,71 % |
| PBO moyen | 18,21 % |
| PBO maximum | 31,43 % |
| Résultats sous 20 % | 3 sur 4 |

Les configurations exactes et la matrice des candidats demeurent non publiées. Les agrégats réduisent le risque apparent de surapprentissage sans démontrer son absence.

## Tableau 6.4 - Moving-block bootstrap face aux références

| Référence | Écart de CAGR | Surperformance log. | IC 95 % | P-value | Verdict officiel |
|---|---:|---:|---:|---:|---|
| HMM 3 états | 49,12 % | 38,89 % | [16,03 % ; 60,91 %] | 0,08 % | Significatif |
| Moyennes mobiles 50/200 | 31,41 % | 23,07 % | [-1,04 % ; 50,29 %] | 4,92 % | Non significatif |
| Allocation fixe 50 % | 29,74 % | 21,70 % | [10,49 % ; 34,23 %] | 0,14 % | Significatif |
| Momentum 270 jours | 29,59 % | 21,58 % | [-0,83 % ; 47,75 %] | 4,66 % | Non significatif |
| Momentum 180 jours | 22,94 % | 16,31 % | [-7,46 % ; 42,35 %] | 11,32 % | Non significatif |
| Ciblage volatilité 30 jours | 21,30 % | 15,05 % | [-8,00 % ; 37,48 %] | 7,84 % | Non significatif |
| Ciblage volatilité 14 jours | 19,20 % | 13,46 % | [-8,84 % ; 34,86 %] | 9,80 % | Non significatif |
| Momentum 90 jours | 15,48 % | 10,70 % | [-12,69 % ; 30,97 %] | 14,60 % | Non significatif |
| Bitcoin passif | 13,89 % | 9,55 % | [-21,04 % ; 39,54 %] | 24,58 % | Non significatif |
| Momentum 30 jours | 13,29 % | 9,12 % | [-11,33 % ; 30,99 %] | 22,02 % | Non significatif |
| Momentum 60 jours | 6,18 % | 4,14 % | [-17,42 % ; 22,47 %] | 29,95 % | Non significatif |

Règle contrôlée : le verdict est positif uniquement si la p-value unilatérale est inférieure à 5 % et si la borne basse de l'intervalle à 95 % est strictement positive.

Les onze écarts de CAGR sont positifs. Deux comparaisons sur onze satisfont la règle complète : allocation fixe à 50 % et HMM à trois états.

## Tableau 6.5A - Sensibilité Newey-West du Sharpe

| Retards | Sharpe HAC | Inflation de volatilité |
|---:|---:|---:|
| 5 | 1,5964 | 0,9946 |
| 7 | 1,5896 | 0,9988 |
| 10 | 1,5740 | 1,0087 |
| 21 | 1,4932 | 1,0633 |
| 30 | 1,4410 | 1,1018 |
| 60 | 1,3472 | 1,1785 |

Le choix canonique de vingt et un retards réduit le Sharpe annualisé de 1,5877 à 1,4932.

Aucun calcul HAC équivalent du bitcoin passif n'est présent dans l'artefact applicable.

## Tableau 6.5B - Bootstrap circulaire du Sharpe

| Taille de bloc | Médiane | Borne basse 95 % | Borne haute 95 % | Part positive |
|---:|---:|---:|---:|---:|
| 5 | 1,5833 | 0,7832 | 2,3419 | 100,0 % |
| 10 | 1,5901 | 0,8143 | 2,3733 | 100,0 % |
| 21 | 1,5669 | 0,7572 | 2,3501 | 100,0 % |
| 30 | 1,5964 | 0,7837 | 2,4057 | 100,0 % |
| 60 | 1,5767 | 0,7608 | 2,4466 | 100,0 % |

## Tableau 6.5C - Diagnostics de Ljung-Box

| Série | Retards | Statistique | P-value |
|---|---:|---:|---:|
| Rendements | 5 | 4,0000 | 0,549415 |
| Rendements | 10 | 12,9009 | 0,229263 |
| Rendements | 21 | 42,8721 | 0,003264 |
| Rendements | 30 | 65,1629 | 0,000209 |
| Rendements centrés au carré | 5 | 141,0192 | 1,09e-28 |
| Rendements centrés au carré | 10 | 231,0325 | 5,22e-44 |
| Rendements centrés au carré | 21 | 433,4775 | 1,07e-78 |
| Rendements centrés au carré | 30 | 487,9547 | 3,55e-84 |

## Tableau 6.6 - Lecture consolidée

| Dimension | Résultat contrôlé | Lecture autorisée |
|---|---|---|
| Sharpe probabiliste | 99,9967 % | Probabilité très élevée sous les hypothèses du test ; dépendance sérielle non explicitement corrigée |
| Sharpe déflaté | 99,9967 % | Résultat favorable après prise en compte de quinze essais agrégés ; matrice privée |
| Tests multiples | P-values publiées à zéro | Résultat favorable, borné par la résolution des 2 000 répétitions |
| PBO | Médiane 15,71 % | Risque de surapprentissage réduit mais non annulé |
| Bootstrap contre les références | 11 écarts positifs, 2 significatifs | La surperformance historique n'est pas universellement significative |
| Dépendance temporelle | Sharpe HAC 21 = 1,4932 | Le résultat reste positif après correction linéaire de la dépendance temporelle |
| Bootstrap circulaire | Toutes les bornes basses positives | Robustesse favorable sur les tailles de bloc publiées, conditionnelle au jeu de sensibilité |

## Limites obligatoires

- L'analyse est historique et rétrospective ; elle ne constitue pas une validation indépendante.
- Les matrices de candidats, observations rééchantillonnées et configurations exactes restent non publiées.
- Newey-West traite la dépendance sérielle linéaire sans modéliser l'intégralité de la distribution conditionnelle.
- Les conclusions bootstrap demeurent conditionnelles aux tailles de bloc et répétitions publiées.
- Aucun résultat ne démontre l'absence de surapprentissage ni ne garantit une performance future.
