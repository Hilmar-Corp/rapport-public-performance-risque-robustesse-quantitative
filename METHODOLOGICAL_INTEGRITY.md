# Standard d’intégrité et d’honnêteté méthodologique

## Objet

Le présent standard encadre la conception, l’interprétation et la publication
des analyses quantitatives relatives à Nostra AI.

Il vise à empêcher :

- la sélection opportuniste des résultats ;
- la présentation asymétrique des conclusions ;
- la confusion entre backtest, shadow live, pilote et production client ;
- la surestimation de la significativité statistique ;
- la dissimulation de limites ou de résultats défavorables ;
- la modification rétroactive d’un protocole sans traçabilité.

## Principes directeurs

### 1. Définition préalable du périmètre

Toute analyse doit identifier avant interprétation :

- la période observée ;
- la fréquence ;
- les actifs concernés ;
- les conventions d’exposition ;
- les coûts et délais d’exécution ;
- les benchmarks ;
- les métriques ;
- les hypothèses ;
- les limites d’usage.

### 2. Symétrie de présentation

Les résultats favorables et défavorables doivent être présentés selon un
niveau de précision comparable.

Une communication ne doit pas :

- mettre en avant une métrique favorable tout en omettant une métrique
  défavorable matériellement pertinente ;
- présenter un sous-échantillon favorable comme représentatif de l’ensemble ;
- masquer l’absence de significativité statistique ;
- confondre absence de rejet statistique et preuve d’équivalence ;
- extrapoler un résultat historique au-delà de son périmètre.

### 3. Absence de sélection opportuniste

La publication doit tenir compte :

- du nombre de stratégies ou candidats évalués ;
- du risque de data snooping ;
- du risque de multiple testing ;
- du risque de surajustement ;
- des changements successifs de spécification ;
- de la dépendance temporelle des observations.

Les méthodes de contrôle utilisées doivent être identifiées lorsque
matériellement pertinentes : DSR, White Reality Check, Hansen SPA, CSCV/PBO,
bootstrap ou autres méthodes documentées.

### 4. Séparation des catégories de preuve

| Catégorie | Signification autorisée |
|---|---|
| `code-reproducible` | Le résultat peut être recalculé depuis le code et les données publiques prévues |
| `artifact-verified` | Le résultat est vérifié à partir d’un artefact contrôlé, sans publication de la logique propriétaire |
| `historical evidence` | Le résultat décrit une période passée et ne constitue pas une prévision |
| `shadow-live evidence` | Le système fonctionne sur données réelles et infrastructure de production sans usage contractuel client |
| `pilot evidence` | Le résultat provient d’un pilote défini et gouverné |
| `independent validation` | Une partie suffisamment indépendante a réalisé une validation formelle |

Le dépôt ne revendique pas une validation indépendante de Nostra AI.

### 5. Distinction entre observation et interprétation

Une publication doit distinguer :

- les valeurs directement observées ;
- les résultats calculés ;
- les tests statistiques ;
- les interprétations ;
- les inférences ;
- les limitations ;
- les éléments non démontrés.

Toute inférence doit être présentée comme telle et ne doit pas être formulée
comme une certitude empirique.

### 6. Prudence statistique

La significativité individuelle de certaines comparaisons ne doit pas être
présentée comme une significativité universelle.

Une valeur p, un Sharpe, un CAGR ou un drawdown ne suffit pas isolément à
établir :

- la persistance future ;
- l’absence de surajustement ;
- la capacité réelle d’exécution ;
- l’aptitude à la production ;
- l’adéquation à un client ;
- la conformité réglementaire.

### 7. Réalisme économique

Les analyses doivent expliciter, selon leur périmètre :

- les coûts ;
- le spread ;
- le slippage ;
- l’impact de marché ;
- la rotation ;
- les délais ;
- la liquidité ;
- la participation ;
- les limites de capacité.

Une surface synthétique ou générique de capacité ne doit pas être présentée
comme une capacité réelle contractuellement exécutable.

### 8. Traçabilité des changements

Toute modification matérielle d’une méthode, d’un benchmark, d’une période,
d’une métrique ou d’une interprétation doit être :

- versionnée ;
- expliquée ;
- revue ;
- testée ;
- reliée au change control applicable.

Une campagne figée ne peut pas être rouverte afin d’améliorer rétrospectivement
les résultats publiés.

### 9. Publication des limites

Les limites suivantes doivent être rappelées lorsqu’elles sont pertinentes :

- résultats historiques ;
- absence de garantie future ;
- frontière propriétaire ;
- absence de validation indépendante ;
- absence de certification réglementaire ;
- absence de calibration réelle de capacité ;
- distinction entre shadow live, pilote et production client.

### 10. Correction des erreurs

Une erreur matérielle doit être corrigée même lorsqu’elle affecte
défavorablement une conclusion publiée.

La correction doit préciser :

- la nature de l’erreur ;
- le périmètre affecté ;
- la version concernée ;
- la décision de réouverture ou non ;
- les résultats corrigés ;
- les mesures préventives.

## Expressions interdites sans preuve correspondante

Ne doivent pas être utilisées sans base formelle :

- « performance garantie » ;
- « sans risque » ;
- « validé indépendamment » ;
- « capacité institutionnelle démontrée » ;
- « significatif dans tous les cas » ;
- « robuste à toutes les conditions de marché » ;
- « prêt pour tout usage de production » ;
- « totalement reproductible » lorsque les résultats sont seulement
  `artifact-verified`.

## Revue préalable à la publication

Avant toute publication quantitative, les questions suivantes doivent être
résolues :

1. Le périmètre est-il défini ?
2. Les conventions sont-elles explicites ?
3. Les coûts et délais sont-ils traités ?
4. Les résultats défavorables sont-ils visibles ?
5. Les risques de multiple testing sont-ils traités ?
6. Le niveau de reproductibilité est-il correctement qualifié ?
7. Les affirmations dépassent-elles les preuves disponibles ?
8. Les limites sont-elles suffisamment visibles ?
9. La frontière de propriété intellectuelle est-elle respectée ?
10. La publication est-elle reliée à une version et à une preuve contrôlée ?

## Statut de v0.3.0

La campagne historique de v0.3.0 est figée.

Aucune optimisation historique supplémentaire, sélection de champion,
extension opportuniste de benchmarks ou modification guidée par les résultats
n’est autorisée dans cette version.

Les conditions de réouverture sont limitées à :

1. un défaut matériel de données ;
2. un défaut matériel d’implémentation ;
3. un changement de modèle approuvé par la gouvernance ;
4. de nouvelles preuves live ou pilote nécessitant une outcome analysis
   formelle.

## Documents associés

- `METHODOLOGY.md` ;
- `PROPRIETARY_BOUNDARY.md` ;
- `REPRODUCIBILITY.md` ;
- `CHANGE_CONTROL.md` ;
- `docs/QUANTITATIVE_VALIDATION_ROADMAP.md` ;
- `docs/QUANTITATIVE_RESEARCH_FREEZE_V0.3.0.md`.
