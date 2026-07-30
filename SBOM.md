# Nomenclature des composants logiciels

Une nomenclature CycloneDX JSON des dépendances est générée à partir de l’ensemble exact et contrôlé des contraintes Python 3.13.

Cette nomenclature est jointe à chaque publication formelle GitHub au lieu d’être enregistrée dans l’arbre Git, car les métadonnées CycloneDX peuvent contenir des champs propres à chaque génération.

L’ensemble canonique des dépendances est consigné dans :

`requirements/constraints-py313.txt`

Régénération :

    pip-audit       -r requirements/constraints-py313.txt       --format cyclonedx-json       --output sbom.cdx.json
