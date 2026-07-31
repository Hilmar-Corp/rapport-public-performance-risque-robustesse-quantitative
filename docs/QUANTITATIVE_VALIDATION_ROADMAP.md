# Roadmap de validation quantitative v0.3.0

## Objet

Cette roadmap consolide les contrôles quantitatifs du paquet public de preuves
HilmarCorp. Elle distingue le code public, les résultats publics, les preuves
privées engagées par SHA-256 et les développements encore requis.

Elle ne constitue ni une validation indépendante, ni une certification
réglementaire, ni une promesse de performance future.

## Périmètre réconcilié

La matrice publique couvre 23 contrôles :

- backtest, causalité et absence de look-ahead ;
- overfitting, data snooping, PBO et bootstrap ;
- non-stationnarité, drift et régimes ;
- coûts, délais et placebos ;
- VaR, Expected Shortfall, Monte Carlo et risques de queue ;
- stress, sensibilité, ablations et résilience des données ;
- monitoring, outcome analysis et gouvernance de publication.

Les preuves privées ne sont pas publiées. Leur existence est engagée par des
commitments SHA-256 calculés sur des manifestes canoniques ne contenant aucun
chemin privé.

## Développements quantitatifs restant à réaliser

1. Formalisation de l’outcome analysis backtest/shadow/live.

## Développements génériques réalisés dans PR 14

- stress paramétrable de slippage ;
- décomposition frais, demi-spread, slippage et impact ;
- loi d’impact générique dépendant du notionnel, de la participation et de
  la volatilité ;
- limite de participation ;
- capacité économique et break-even ;
- surface synthétique déterministe ;
- intégration optionnelle au backtest sans modification du mode historique.

Ces développements ne constituent pas une calibration réelle de Nostra.

## Exports publics restant à produire

Les résultats existants doivent être revus puis exportés sous forme agrégée
pour les contrôles suivants :

- PSR, DSR, White Reality Check, Hansen SPA, CSCV/PBO et bootstrap ;
- ADF, KPSS, CUSUM et drift ;
- performance par régime ;
- surface coûts × délais ;
- placebos et permutations ;
- VaR, Expected Shortfall et Monte Carlo ;
- résilience des données, sensibilité et ablations ;
- monitoring et outcomes.

## Frontière de propriété intellectuelle

Ne doivent pas être publiés :

- les positions ou rendements quotidiens Nostra ;
- les traces de signal historiques ;
- les variables, coefficients et seuils propriétaires ;
- les configurations de production ;
- les artefacts de recherche internes ;
- les données ou identifiants de fournisseurs privés.

Les publications autorisées sont limitées au code générique, aux résultats
agrégés, aux limites, aux conclusions défavorables et aux engagements
cryptographiques de preuves privées.

## Séquence de livraison

- PR 13 — matrice de contrôle et engagements de preuves ;
- PR 14 — slippage, impact de marché et capacité ;
- PR 15 — exports quantitatifs publics agrégés ;
- PR 16 — rapport intégré et documentation ;
- PR 17 — durcissement de release et v0.3.0.

Les releases v0.2.0 et v0.2.1 restent immuables.
