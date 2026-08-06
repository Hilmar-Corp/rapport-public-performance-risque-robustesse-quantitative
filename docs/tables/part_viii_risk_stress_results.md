# Partie VIII — Risque, drawdowns et stress

Paquet institutionnel construit à partir des six exports quantitatifs gelés de la release v0.3.0.

## Tableau 8.1 — Risque de queue historique quotidien

| Indicateur | Nostra AI | Bitcoin passif |
|---|---:|---:|
| VaR historique 95 % | 2,04 % | 4,63 % |
| Expected Shortfall 95 % | 3,21 % | 6,87 % |
| VaR historique 99 % | 3,88 % | 8,28 % |
| Expected Shortfall 99 % | 5,30 % | 10,79 % |
| Pire rendement quotidien | -9,36 % | -15,38 % |
| Meilleur rendement quotidien | 9,57 % | 19,54 % |

Les estimations sont historiques et ne constituent pas des bornes de perte futures.

## Tableau 8.2 — Backtesting canonique de la VaR et de l'ES

| Horizon | Niveau | Observations | Exceptions | Taux observé | Taux attendu | Kupiec | Binomial exact | Indépendance | Couverture conditionnelle | ES bootstrap | Statut |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 j | 95 % | 1846 | 93 | 5,04 % | 92,30 / 1846 | 0,9405 | 0,9150 | 0,1393 | 0,3344 | 0,3853 | GREEN |
| 1 j | 99 % | 1846 | 21 | 1,14 % | 18,46 / 1846 | 0,5610 | 0,5569 | 0,4868 | 0,6631 | 0,1764 | GREEN |
| 10 j | 95 % | 184 | 11 | 5,98 % | 9,20 / 184 | 0,5542 | 0,4976 | 0,2354 | 0,4152 | 0,2369 | GREEN |
| 10 j | 99 % | 184 | 4 | 2,17 % | 1,84 / 184 | 0,1661 | 0,1143 | 0,6724 | 0,3505 | 0,1064 | AMBER |

La spécification canonique utilise une fenêtre glissante de 365 jours. Le test à dix jours et 99 % est classé AMBER en raison du faible nombre attendu d'exceptions.

## Tableau 8.3 — Drawdowns, durées et récupération

| Indicateur | Nostra AI | Bitcoin passif |
|---|---:|---:|
| Nombre d'épisodes | 104 | 50 |
| Perte maximale | -21,39 % | -76,63 % |
| Profondeur médiane | 1,60 % | 3,84 % |
| Profondeur au quantile 95 % | 14,08 % | 39,89 % |
| Durée observée médiane | 4,0 | 4,5 |
| Durée observée maximale | 239 | 847 |
| Part du temps sous le précédent plus-haut | 91,68 % | 95,57 % |
| Taux de récupération | 99,04 % | 98,00 % |
| Épisodes non récupérés à la clôture | 1 | 1 |

Les épisodes non récupérés sont censurés à droite. Les durées observées ne constituent pas des prévisions de récupération.

## Tableau 8.4 — Monte-Carlo historique par blocs

| Portefeuille | Bloc | Perte terminale | Drawdown < -20 % | Drawdown < -30 % | Sharpe positif | Rendement terminal médian | Drawdown médian |
|---|---:|---:|---:|---:|---:|---:|---:|
| Bitcoin passif | 7 j | 28,35 % | 97,85 % | 78,24 % | 80,63 % | 39,24 % | -39,18 % |
| Bitcoin passif | 21 j | 27,93 % | 97,73 % | 77,52 % | 80,95 % | 41,41 % | -39,50 % |
| Bitcoin passif | 30 j | 28,38 % | 98,02 % | 77,10 % | 80,04 % | 41,59 % | -40,35 % |
| Bitcoin passif | 60 j | 30,08 % | 97,77 % | 76,30 % | 78,00 % | 42,36 % | -40,35 % |
| Nostra AI | 7 j | 6,53 % | 29,75 % | 4,26 % | 95,28 % | 51,34 % | -16,82 % |
| Nostra AI | 21 j | 7,02 % | 25,87 % | 3,02 % | 94,59 % | 51,57 % | -16,19 % |
| Nostra AI | 30 j | 7,60 % | 25,41 % | 2,96 % | 94,15 % | 52,42 % | -16,11 % |
| Nostra AI | 60 j | 8,57 % | 24,08 % | 2,26 % | 93,10 % | 51,51 % | -16,42 % |

Chaque configuration comprend 10 000 trajectoires de 365 jours. Les deux séries sont rééchantillonnées conjointement afin de préserver leur relation historique dans les blocs sélectionnés.

Selon la taille de bloc, Nostra AI termine devant le bitcoin dans 54,82 % à 58,07 % des trajectoires et présente un drawdown inférieur dans 99,99 % à 100 % des trajectoires.

## Tableau 8.5 — Reverse stress historique

| Seuil de perte sur la NAV | Franchi historiquement | Épisodes | Observations médianes jusqu'au franchissement | Réduction à la date du franchissement | Réduction d'au moins 25 % avant franchissement |
|---:|---|---:|---:|---:|---:|
| 5 % | Oui | 25 | 6,0 | 52,00 % | 24,00 % |
| 10 % | Oui | 10 | 13,5 | 60,00 % | 40,00 % |
| 15 % | Oui | 4 | 26,5 | 25,00 % | 25,00 % |
| 20 % | Oui | 1 | 167,0 | 100,00 % | 100,00 % |
| 25 % | Non | 0 | Non applicable | Non applicable | Non applicable |
| 30 % | Non | 0 | Non applicable | Non applicable | Non applicable |

Les pertes de 25 % et 30 % n'ont pas été observées dans l'historique. Ce non-franchissement ne constitue pas une borne de perte.

La réduction de l'allocation n'a été ni immédiate ni universelle avant les franchissements matériels.

## Tableau 8.6 — Reverse stress contrefactuel

| Indicateur | Résultat |
|---|---:|
| Scénarios totaux | 4908 |
| Scénarios au stade de l'inférence | 67 |
| Scénarios de réentraînement et du cœur directionnel | 132 |
| Scénarios de raffinement | 4709 |
| Frontières de rupture raffinées | 87 |
| Familles de rupture | 8 |
| Répétitions aléatoires de bruit | 30 |
| Répétitions d'injection d'état défavorable | 50 |
| Rupture isolée par corruption d'entrée identifiée | Non |

La classe de vulnérabilité dominante est la fraîcheur et l'intégrité du cœur directionnel.

Les réglages exacts, les variables internes, les trajectoires quotidiennes et les frontières numériques privées ne sont pas publiés.

## Lecture consolidée

- Les mesures historiques de VaR, d'Expected Shortfall et de perte quotidienne sont inférieures à celles du bitcoin passif.
- La spécification canonique de backtesting VaR/ES à 365 jours ne présente aucune réjection formelle au seuil de 5 %.
- Le test à dix jours au seuil de 99 % demeure de faible puissance.
- La fenêtre de calibration de 250 jours n'est pas approuvée pour les mesures de risque de queue à 99 %.
- Les drawdowns de Nostra AI sont moins profonds et leur épisode maximal observé est plus court que pour le bitcoin passif.
- Le dernier drawdown de Nostra AI est non récupéré à la clôture et censuré à droite.
- Dans les simulations historiques par blocs, Nostra AI présente un drawdown inférieur au bitcoin dans 99,99 % à 100 % des trajectoires.
- Nostra AI termine devant le bitcoin dans 54,82 % à 58,07 % des trajectoires simulées.
- La réduction d'allocation avant ou au franchissement d'une perte n'est ni immédiate ni universelle dans l'historique.
- Le reverse stress contrefactuel couvre 4 908 scénarios, 87 frontières raffinées et huit familles de rupture.
- La vulnérabilité dominante concerne la fraîcheur et l'intégrité du cœur directionnel.

### Limites

- Toutes les analyses sont historiques, rétrospectives et non prédictives.
- Les mesures de queue historiques ne constituent pas des bornes de perte.
- Les trajectoires Monte-Carlo sont des recombinaisons de séquences historiques.
- Les durées de drawdown observées ne constituent pas des prévisions de récupération.
- Les non-franchissements historiques de 25 % et 30 % ne démontrent pas que ces pertes sont impossibles.
- Les trajectoires quotidiennes, variables internes, réglages exacts et frontières privées ne sont pas publiés.
- Aucune validation externe indépendante n'est revendiquée.
