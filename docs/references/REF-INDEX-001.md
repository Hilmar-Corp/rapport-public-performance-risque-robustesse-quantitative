# REF-INDEX-001 — Registre maître des références

| ID | Référence courte | Usage principal dans HC-RPT-PUB-001 |
|---|---|---|
| R-STAT-01 | Sharpe (1994) | Définition et interprétation du ratio de Sharpe |
| R-STAT-02 | Bailey & López de Prado (2012/13) | Probabilistic Sharpe Ratio |
| R-STAT-03 | Bailey & López de Prado (2014) | Deflated Sharpe Ratio |
| R-STAT-04 | White (2000) | Reality Check / tests multiples |
| R-STAT-05 | Hansen (2005) | Superior Predictive Ability |
| R-STAT-06 | Bailey et al. (2017) | CSCV / Probability of Backtest Overfitting |
| R-STAT-07 | Künsch (1989) | Rééchantillonnage par blocs pour séries dépendantes |
| R-STAT-08 | Politis & Romano (1992) | Rééchantillonnage circulaire par blocs |
| R-STAT-09 | Newey & West (1987) | Variance HAC / dépendance temporelle |
| R-STAT-10 | Ljung & Box (1978) | Diagnostic d'autocorrélation |
| R-STAT-11 | Dickey & Fuller (1979) | Test de racine unitaire |
| R-STAT-12 | Kwiatkowski et al. (1992) | Test KPSS de stationnarité |
| R-STAT-13 | Brown, Durbin & Evans (1975) | CUSUM / stabilité temporelle |
| R-STAT-14 | Rabiner (1989) | Modèles de Markov cachés |
| R-STAT-15 | Lo (2002) | Propriétés statistiques et annualisation du Sharpe |
| R-STAT-16 | Moskowitz, Ooi & Pedersen (2012) | Momentum en série temporelle |
| R-STAT-17 | Brock, Lakonishok & LeBaron (1992) | Moyennes mobiles / règles techniques |
| R-STAT-18 | Moreira & Muir (2017) | Gestion dynamique selon la volatilité |
| R-STAT-19 | Massey (1951) | Test de Kolmogorov-Smirnov |
| R-STAT-20 | Hamilton (1989) | Régimes markoviens en séries temporelles |
| R-STAT-21 | Andrews (1993) | Ruptures structurelles / instabilité paramétrique |
| R-RISK-01 | Acerbi & Tasche (2002) | Expected Shortfall |
| R-RISK-02 | Kupiec (1995) | Contrôle de couverture de VaR |
| R-RISK-03 | Christoffersen (1998) | Couverture conditionnelle et indépendance |
| R-RISK-04 | Basel Committee (1996) | Cadre institutionnel de backtesting VaR |
| R-RISK-05 | Basel Committee (2018) | Principes de stress testing |
| R-RISK-06 | Basel Framework RMA30 | Reverse stress testing / vulnérabilités |
| R-EXEC-01 | Perold (1988) | Implementation shortfall / coût d’implémentation |
| R-EXEC-02 | Almgren & Chriss (2001) | Exécution optimale et impact de marché |
| R-EXEC-03 | Kyle (1985) | Profondeur, liquidité et impact |
| R-EXEC-04 | Hasbrouck (1991) | Impact informationnel des transactions |
| R-EXEC-05 | Glosten & Milgrom (1985) | Écart acheteur-vendeur et microstructure |
| R-DATA-01 | Binance Spot API | Série et documentation de marché BTCUSDT |
| R-DATA-02 | Kraken API Center | Source secondaire de marché / contrôle |
| R-TECH-01 | NIST FIPS 180-4 | SHA-256 / intégrité |
| R-TECH-02 | SPDX | SBOM / nomenclature logicielle |
| R-TECH-03 | CycloneDX | SBOM / nomenclature logicielle |
| R-TECH-04 | OCI Image Specification | Image OCI et digest |
| R-TECH-05 | GitHub Artifact Attestations | Provenance et attestations d'artefacts |

## Correspondance recommandée avec le rapport

- Partie IV, stratégies de momentum : R-STAT-16.
- Partie IV, croisement de moyennes mobiles : R-STAT-17.
- Partie IV, ciblage de volatilité : R-STAT-18.
- §4.7, modèles de régimes : R-STAT-14, R-STAT-20.
- §6.6, dépendance temporelle du Sharpe : R-STAT-09, R-STAT-10, R-STAT-15.
- Partie VII, dérive des distributions / KS : R-STAT-19.
- Partie VII, stabilité et ruptures : R-STAT-13, R-STAT-21.
- Partie VIII, backtesting VaR : R-RISK-02, R-RISK-03, R-RISK-04.
- Partie VIII, stress testing et reverse stress : R-RISK-05, R-RISK-06.
- Partie IX, coûts, glissement, liquidité, impact et capacité : R-EXEC-01 à R-EXEC-05.
- §4.1 : R-DATA-01.
- §4.7 : R-STAT-14.
- §6.1 : R-STAT-02.
- §6.2 : R-STAT-03.
- §6.3 : R-STAT-04, R-STAT-05.
- §6.4 : R-STAT-06.
- §6.5 : R-STAT-07.
- §6.6 : R-STAT-08, R-STAT-09, R-STAT-10.
- §7.1 : R-STAT-11, R-STAT-12, R-STAT-13.
- Partie VIII, VaR / perte moyenne au-delà du seuil : R-RISK-01, R-RISK-02, R-RISK-03.
- §9.5 : R-DATA-02.
- §3.6 et §10.9 : R-TECH-01.
- Partie X, SBOM : R-TECH-02, R-TECH-03.
- Partie X, OCI : R-TECH-04.
- Partie X, attestations : R-TECH-05.
