# Binance Public API Reference

Quick reference for endpoints used by this skill. All are public — no API key required.

## Base URL
```
https://api.binance.com/api/v3
```

---

## Endpoints Used

### Current Price
```
GET /ticker/price?symbol=SOLUSDT
```
Returns: `{ "symbol": "SOLUSDT", "price": "148.23" }`

---

### 24-Hour Statistics
```
GET /ticker/24hr?symbol=SOLUSDT
```
Key fields:
- `lastPrice` — current market price
- `priceChangePercent` — 24h % change
- `highPrice`, `lowPrice` — 24h range
- `volume` — base asset volume
- `quoteVolume` — quote asset volume
- `count` — number of trades

---

### OHLCV Candlestick Data
```
GET /klines?symbol=SOLUSDT&interval=1h&limit=100
```
Returns array of arrays:
```
[open_time, open, high, low, close, volume, close_time,
 quote_vol, num_trades, taker_buy_vol, taker_buy_quote_vol, ignore]
```

**Valid intervals:** `1m 3m 5m 15m 30m 1h 2h 4h 6h 8h 12h 1d 3d 1w 1M`

**Limit:** Max 500 candles per request. Default 500. Use 100 for standard analysis.

---

### Order Book Depth
```
GET /depth?symbol=SOLUSDT&limit=20
```
Returns: `{ "bids": [[price, qty], ...], "asks": [[price, qty], ...] }`

Valid limits: 5, 10, 20, 50, 100, 500, 1000, 5000

---

### Recent Trades
```
GET /trades?symbol=SOLUSDT&limit=100
```
Returns array of trades:
- `price`, `qty`, `time`, `isBuyerMaker` (false = taker buy)

---

## Rate Limits

Binance Public API is generous for read-only requests:
- **Weight limit:** 6000 per minute (each endpoint costs 1–50 weight)
- `/klines` — weight: 2
- `/ticker/24hr` — weight: 2
- `/depth` — weight: 2–250 (based on limit)
- `/trades` — weight: 25

For multi-pair scans, stay well within limits by processing ≤ 10 pairs at once.

---

## Error Codes

| Code | Meaning | Action |
|---|---|---|
| -1121 | Invalid symbol | Check pair name; append USDT if needed |
| -1100 | Bad request parameter | Check interval string or limit value |
| 429 | Rate limit exceeded | Wait 60s before retrying |
| 418 | IP banned (too many 429s) | Stop all requests immediately |

---

## Supported Pairs (Common)

| Symbol | Name |
|---|---|
| BTCUSDT | Bitcoin |
| ETHUSDT | Ethereum |
| SOLUSDT | Solana |
| BNBUSDT | BNB |
| XRPUSDT | XRP |
| DOGEUSDT | Dogecoin |
| ADAUSDT | Cardano |
| AVAXUSDT | Avalanche |
| DOTUSDT | Polkadot |
| LINKUSDT | Chainlink |
| MATICUSDT | Polygon |
| UNIUSDT | Uniswap |

To check if a pair is valid, call `/ticker/price?symbol=PAIRUSDT`. If it returns an error, the pair doesn't exist.
