# Partie X - Assurance computationnelle

## Tableau 10.1

### Contrôles automatisés et environnement

| Élément | Résultat contrôlé |
|---|---|
| Tests pytest collectés | 393 |
| Couverture de branches exigée | Oui |
| Seuil minimal de couverture | 100 % |
| Pyright | strict |
| Ruff | Cible py311 |
| Versions Python CI | 3.11, 3.12, 3.13 |
| Systèmes CI | macos-latest, ubuntu-latest |
| Environnement canonique | Python 3.13 |

## Tableau 10.2

### Recalcul indépendant du noyau comptable

| Mesure | Écart absolu maximal |
|---|---:|
| Rendement officiel | 4.961e-16 |
| Equity officielle | 3.428e-13 |
| Capital final | 4.459e-09 |
| CAGR | 3.223e-09 |
| Volatilité annualisée | 4.775e-09 |
| Ratio de Sharpe | 4.818e-09 |
| Perte maximale | 4.963e-09 |
| Rotation cumulée | 6.736e-10 |

Le recalcul est réalisé par une implémentation autonome n'important aucune fonction de `src/hilmarbench`.

Cette indépendance porte sur l'implémentation comptable. Elle ne constitue ni une validation externe indépendante de Nostra AI, ni une reproduction publique de la logique propriétaire du modèle.

## Tableau 10.3

### Chaîne logicielle et release

| Contrôle | Présence dans l'architecture |
|---|---|
| Contraintes exactes Python | Oui |
| Reproduction OCI | Oui |
| SBOM CycloneDX | Oui |
| SBOM SPDX | Oui |
| Attestation GitHub OIDC | Oui |
| CodeQL | Oui |
| Dependency review | Oui |
| Audit des dépendances | Oui |
| Sauvegarde et restauration du dépôt | Oui |

## Classes de preuve

| Élément | Classe |
|---|---|
| Benchmarks publics | `code-reproducible` |
| Résultats agrégés Nostra AI | `artifact-verified` |
| Preuves détaillées privées | `private-controlled` |
| Validation externe indépendante | Non revendiquée |

## Limites

- Le recalcul autonome porte sur le noyau comptable et ne constitue pas une reproduction publique de la logique propriétaire de Nostra AI.
- L'indépendance d'implémentation du recalcul comptable ne constitue pas une validation externe indépendante.
- Une couverture de code complète démontre l'exécution des chemins mesurés, non l'exhaustivité des hypothèses économiques.
- Les SBOM, manifestes, empreintes et attestations établissent la provenance et l'intégrité des artefacts ; ils ne démontrent pas la validité économique future du modèle.
- La reproductibilité publique de Nostra AI reste limitée par la frontière propriétaire explicitement documentée.

Conclusion contrôlée : l'architecture publique fournit une assurance computationnelle substantielle sur le noyau comptable, les contrôles automatisés, la reproductibilité des composants publics, la provenance, la sécurité de la chaîne logicielle et l'intégrité des artefacts. Cette assurance ne doit pas être confondue avec une validation externe indépendante de Nostra AI ni avec une garantie de validité économique future.
