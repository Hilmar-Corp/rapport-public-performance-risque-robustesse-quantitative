# Sécurité de la chaîne d’approvisionnement

Le dépôt applique les contrôles suivants :

- les actions GitHub sont verrouillées sur des SHA de commits immuables ;
- l’environnement contrôlé Python 3.13 est défini par des contraintes exactes ;
- les dépendances sont auditées avec `pip-audit` ;
- une nomenclature CycloneDX des dépendances est générée pour chaque publication formelle ;
- CodeQL réalise une analyse statique de sécurité ;
- Dependabot surveille les dépendances Python et GitHub Actions ;
- les fichiers de publication sont protégés par des manifestes SHA-256 ;
- les identifiants de production, les points d’accès et les modèles propriétaires sérialisés sont interdits dans le dépôt public.

Les tests de compatibilité couvrent un périmètre plus large que l’environnement exact de reproduction : Python 3.11, 3.12 et 3.13 sont testés sous Ubuntu, tandis que Python 3.13 est également testé sous macOS.
