# Reverse stress contrefactuel - preuve publique agrégée

## Objet

Le contrôle `QNT-RST-002` documente une campagne privée de reverse stress
contrefactuel appliquée à la chaîne propriétaire de décision de Nostra AI.

Le moteur propriétaire n’est pas publié. La preuve est donc classée
`artifact-verified`, et non `code-reproducible`.

## Couverture

La campagne privée couvre :

- les corruptions des entrées au moment de l’inférence ;
- les corruptions avant réentraînement séquentiel ;
- les valeurs manquantes, pannes contiguës, dérives et bruits ;
- les permutations et corruptions de cible ;
- les défaillances du signal directionnel central ;
- les scénarios conjoints ;
- les grilles fines de raffinement ;
- les répétitions multi-graines ;
- tous les offsets de phase des mises à jour obsolètes.

La baseline privée est réconciliée avec une tolérance inférieure à
`1e-12`.

## Résultat agrégé

L’artefact public indique :

- 4 908 scénarios exécutés ;
- 87 frontières de défaillance raffinées ;
- huit familles de frontières ;
- 50 répétitions d’injection aléatoire d’états adverses ;
- 30 répétitions pour les scénarios de bruit ;
- tous les offsets de phase testés pour les mises à jour obsolètes.

La vulnérabilité historique dominante identifiée concerne l’intégrité et
la fraîcheur du signal directionnel central. Les corruptions isolées de la
couche d’entrée probabiliste sont restées fortement amorties dans le
périmètre testé.

## Séparation de la propriété intellectuelle

Ne sont pas publiés :

- les séries quotidiennes ;
- les rendements et allocations quotidiennes ;
- les variables internes ;
- les coefficients et configurations ;
- les scénarios individuels ;
- les points de rupture numériques détaillés ;
- les traces de réentraînement ;
- les chemins des preuves privées ;
- les données ou identifiants de fournisseurs.

L’artefact public contient uniquement des comptages, des conclusions
agrégées, des limitations et un commitment SHA-256 privé.

## Limites

Cette campagne ne constitue pas :

- une garantie de robustesse future ;
- une validation indépendante ;
- une décision d’aptitude à la production ;
- une validation de la collecte amont ;
- une validation d’exécution ou de capacité ;
- une outcome analysis live de longue durée.
