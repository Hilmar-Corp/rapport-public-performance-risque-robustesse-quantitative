# REF-DATA-001 — Sources de données de marché et provenance documentaire

## R-DATA-01 — Binance

**Source documentaire :** Binance Spot API Documentation.

**Objet dans le rapport :** provenance documentaire de la série quotidienne BTCUSDT utilisée comme série historique de marché dans le périmètre décrit au §4.1.

**Éléments documentés :**
- endpoint public de chandeliers `GET /api/v3/klines` ;
- symbole et intervalle paramétrables ;
- données OHLCV ;
- horodatage ;
- accès à des données historiques via l'infrastructure publique de données de marché Binance.

**Références :**
- https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md
- https://github.com/binance/binance-spot-api-docs/blob/master/faqs/market_data_only.md

**Qualification :** cette documentation établit l'interface et la provenance fournisseur déclarée. Elle ne constitue pas un audit indépendant de l'exactitude économique de la série historique conservée par HilmarCorp.

## R-DATA-02 — Kraken

**Source documentaire :** Kraken API Center.

**Objet dans le rapport :** documentation de la source secondaire de marché utilisée dans le dispositif de contrôle postérieur à l'évaluation historique.

**Références :**
- https://docs.kraken.com/
- https://docs.kraken.com/api/docs/rest-api/get-post-trade
- https://docs.kraken.com/api/docs/rest-api/get-pre-trade

**Qualification :** la documentation Kraken décrit les interfaces publiques de données de marché. L'usage de Kraken comme source secondaire de contrôle ne transforme pas la chaîne en validation indépendante de l'ensemble des données historiques.
