# Méthodologie d’évaluation

Le dispositif d’évaluation analyse des stratégies d’exposition quotidienne au BTC selon un protocole économique et comptable commun.

## Conventions des stratégies publiques de référence

Les stratégies publiques de référence utilisent :

- une fréquence d’évaluation quotidienne ;
- une exposition acheteuse uniquement, bornée entre 0 % et 100 % ;
- une exposition initiale égale à zéro ;
- une rotation brute égale à la variation absolue quotidienne de l’exposition ;
- des coûts de transaction de 25 points de base par unité de rotation ;
- un décalage d’une observation entre la décision d’une stratégie dynamique et son application ;
- un facteur d’annualisation égal à 365 ;
- un CAGR égal à `final_equity ** (365 / observations) - 1`.

## Références publiques

Le paquet public met en œuvre :

- une stratégie d’achat-conservation ;
- une exposition fixe de 50 % ;
- des stratégies de momentum en série temporelle sur 30, 60, 90, 180 et 270 observations ;
- un croisement de moyennes mobiles 50/200 ;
- un ciblage de volatilité sur 14 et 30 observations ;
- un HMM gaussien à trois états fondé uniquement sur les prix et évalué en marche en avant.

Les stratégies publiques de référence sont reproductibles à partir de l’artefact de publication engagé et du code source public.

## Nostra AI

Nostra AI est évaluée selon les mêmes conventions quotidiennes de coûts, de rotation, de décalage d’exécution et d’annualisation.

Sa plage d’exposition gouvernée se distingue de celle des références publiques acheteuses uniquement :

- exposition gouvernée minimale : -10 % ;
- exposition gouvernée maximale : +100 %.

Le dépôt GitHub publie les métriques agrégées de Nostra ainsi qu’un engagement cryptographique portant sur l’artefact privé d’évaluation conservé.

Il ne publie aucune logique du modèle Nostra, aucune caractéristique, aucun paramètre, aucune probabilité, aucune position, aucun rendement quotidien, aucune série quotidienne de valeur liquidative, aucune rotation et aucune trace de coûts de transaction.

Un processus séparé destiné au site internet peut afficher des observations quotidiennes de valeur liquidative avec retard. Cet artefact n’est pas distribué par GitHub et applique un délai minimal de publication de quatorze jours.
