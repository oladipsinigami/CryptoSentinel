# Perception Layer — API Reference

## Bitget Market Data

### Get OHLCV Candles (for Technicals)
```
GET https://api.bitget.com/api/v2/spot/market/candles
Params: symbol=BTCUSDT&granularity=1h&limit=100
```
Response fields: `open`, `high`, `low`, `close`, `volume`, `timestamp`

### Get Current Ticker Price
```
GET https://api.bitget.com/api/v2/spot/market/tickers?symbol=BTCUSDT
```
Extract: `lastPr` (last price), `change24h`, `baseVolume`

### Get Order Book Depth
```
GET https://api.bitget.com/api/v2/spot/market/orderbook?symbol=BTCUSDT&limit=20
```

---

## Fear & Greed Index
```
GET https://api.alternative.me/fng/?limit=1
```
Response: `{ "data": [{ "value": "72", "value_classification": "Greed" }] }`

Score mapping:
- 0–25 → EXTREME FEAR → signal +2 (contrarian buy)
- 26–45 → FEAR → signal +1
- 46–55 → NEUTRAL → signal 0
- 56–75 → GREED → signal -1
- 76–100 → EXTREME GREED → signal -2 (contrarian sell)

---

## BTC Dominance + Global Market Cap
```
GET https://api.coingecko.com/api/v3/global
```
Extract:
- `bitcoin_dominance_percentage` — high dominance (>55%) = risk-off, altcoins weak
- `total_market_cap.usd` — compare to 7-day MA for trend

---

## News Sentiment

### CryptoPanic (free tier)
```
GET https://cryptopanic.com/api/free/v1/posts/?auth_token=YOUR_KEY&currencies=BTC&filter=hot
```
Parse `title` field of each post. Score with simple keyword matching:
- BULLISH keywords: `ETF`, `approval`, `surge`, `rally`, `all-time high`, `adoption`, `institutional`
- BEARISH keywords: `hack`, `ban`, `crash`, `SEC`, `lawsuit`, `fraud`, `FUD`, `dump`
- Aggregate: sum scores / count of articles → normalize to [-3, +3]

### Fallback: RSS Parsing
If CryptoPanic is unavailable, parse these RSS feeds:
- `https://cointelegraph.com/rss`
- `https://coindesk.com/arc/outboundfeeds/rss/`

---

## On-Chain Signals (Glassnode Free Tier)

### Exchange Net Position Change
```
GET https://api.glassnode.com/v1/metrics/transactions/transfers_volume_to_exchanges_sum
Params: a=BTC&i=24h&api_key=YOUR_KEY
```
High inflow to exchanges → bearish (holders preparing to sell)

### Large Transaction Count (Whales)
```
GET https://api.glassnode.com/v1/metrics/transactions/count_above_100k_usd
```
Spike in large transactions → increased whale activity (can be bullish or bearish)

### Fallback: Blockchain.info
If Glassnode is unavailable:
```
GET https://blockchain.info/stats?format=json
```
Extract `n_tx` (transaction count) and `estimated_transaction_volume_usd`

---

## Technical Indicators — Calculation Reference

### RSI (14-period)
```python
delta = prices.diff()
gain = delta.clip(lower=0).rolling(14).mean()
loss = (-delta.clip(upper=0)).rolling(14).mean()
rs = gain / loss
rsi = 100 - (100 / (1 + rs))
```
Signal: RSI < 30 → +2, RSI 30-50 → +1, RSI 50-70 → -1, RSI > 70 → -2

### MACD (12, 26, 9)
```python
ema12 = prices.ewm(span=12).mean()
ema26 = prices.ewm(span=26).mean()
macd = ema12 - ema26
signal_line = macd.ewm(span=9).mean()
histogram = macd - signal_line
```
Signal: histogram > 0 and rising → +2, histogram < 0 and falling → -2

### Bollinger Bands (20, 2)
```python
sma20 = prices.rolling(20).mean()
std20 = prices.rolling(20).std()
upper = sma20 + 2 * std20
lower = sma20 - 2 * std20
```
Signal: price < lower → +2 (oversold), price > upper → -2 (overbought)
