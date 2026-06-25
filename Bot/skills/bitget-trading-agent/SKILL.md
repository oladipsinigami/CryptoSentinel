---
name: bitget-trading-agent
description: >
  Autonomous AI crypto trading agent that runs a full perception → decision → execution → risk management loop using Bitget APIs. Use this skill whenever the user wants to: build or run a trading agent, analyze crypto market signals, make BUY/SELL/HOLD decisions based on news/technicals/on-chain/macro data, place simulated paper trades, manage portfolio risk, run backtests, or generate trading performance reports. Trigger this skill even if the user just says "analyze the market", "should I buy BTC?", "run my trading strategy", "backtest my agent", or "show me the dashboard". This skill is the backbone of the Bitget AI Hackathon S1 Track 1 submission.
---

# Bitget Trading Agent Skill

A fully autonomous AI trading agent covering all four layers required for the Bitget AI Hackathon S1 Track 1:

```
📡 PERCEPTION  →  🧠 DECISION  →  ⚡ EXECUTION  →  🛡️ RISK MANAGEMENT
```

---

## How to Use This Skill

When invoked, first ask the user what they want to do:
1. **Run a full agent cycle** — collect signals → decide → sim trade → log results
2. **Analyze market only** — perception layer only, no trade execution
3. **Review dashboard** — show recent decisions and performance
4. **Run backtest** — replay past signals through the decision engine
5. **Check risk status** — review current exposure and risk limits

Then follow the relevant section below.

---

## Layer 1: Perception (Signal Collection)

Collect data from all 5 sources in parallel. Read `references/perception.md` for detailed API endpoints and parsing logic.

### 1a. News Sentiment
- Fetch latest crypto headlines from CryptoPanic or NewsAPI
- Score each headline: BULLISH (+1), BEARISH (-1), NEUTRAL (0)
- Compute aggregate sentiment score for the target asset (e.g., BTC, ETH)
- Flag any high-impact news (regulatory, exchange hack, ETF approval)

### 1b. Technical Indicators
Run on OHLCV data from Bitget REST API (`GET /api/v2/mix/market/candles`):
- **RSI (14)**: Overbought >70, Oversold <30
- **MACD**: Signal line crossover direction
- **Bollinger Bands (20, 2)**: Price vs upper/lower bands
- **EMA 9/21 crossover**: Trend direction

### 1c. On-Chain Signals
Query via public APIs (Glassnode free tier or Bitget on-chain module):
- Whale wallet movements (>100 BTC transfers)
- Exchange inflow/outflow (high inflow = selling pressure)
- SOPR (Spent Output Profit Ratio) — above 1 = profit taking

### 1d. Macro Conditions
- BTC dominance (from CoinGecko: `GET /api/v3/global`)
- Fear & Greed Index (from `https://api.alternative.me/fng/`)
- Market cap trend (7-day delta)

### 1e. Aggregate Signal Score
Combine all signals into a single score from -10 to +10:
```
score = (sentiment * 2) + (technicals * 3) + (onchain * 2) + (macro * 1.5) + (volume * 1.5)
```
Normalize to range [-10, +10]. Output a perception summary object.

---

## Layer 2: Decision Engine

Read `references/decision.md` for the full decision logic and prompt templates.

Based on the aggregate signal score:

| Score Range | Decision | Confidence |
|-------------|----------|------------|
| +6 to +10   | STRONG BUY  | HIGH |
| +3 to +5.9  | BUY         | MEDIUM |
| -2.9 to +2.9 | HOLD       | LOW |
| -3 to -5.9  | SELL        | MEDIUM |
| -6 to -10   | STRONG SELL | HIGH |

### Decision Prompt Template
Feed the perception summary to the AI with this prompt structure:
```
You are a professional crypto trading analyst. Based on the following market signals,
make a trading decision for [ASSET].

Signal Summary: [PERCEPTION_SUMMARY]
Current Position: [CURRENT_POSITION]
Risk Parameters: [RISK_PARAMS]

Respond with:
- Decision: BUY | SELL | HOLD
- Confidence: HIGH | MEDIUM | LOW  
- Reasoning: (2-3 sentences max)
- Suggested position size: X% of portfolio
- Stop-loss level: $X
```

Always include reasoning. Never make a HIGH confidence decision when signals conflict.

---

## Layer 3: Sim Trade Execution

Run simulated trades only — no real funds. Use `scripts/sim_trader.py` for all execution.

### Placing a Sim Trade
```python
# Use the sim_trader script:
python scripts/sim_trader.py \
  --action BUY \
  --asset BTC \
  --amount_usdt 100 \
  --entry_price <current_price> \
  --stop_loss <stop_price> \
  --take_profit <target_price>
```

### Trade Log Format
Every sim trade is appended to `backtest_log.csv`:
```
timestamp, asset, action, amount_usdt, entry_price, stop_loss, take_profit, 
signal_score, confidence, reasoning, exit_price, pnl_usdt, pnl_pct, status
```

### Getting Current Price
```
GET https://api.bitget.com/api/v2/spot/market/tickers?symbol=BTCUSDT
```
Extract `lastPr` from the response.

---

## Layer 4: Risk Management

Apply these rules before every trade. If any rule is violated, override to HOLD and log the reason.

Read `references/risk.md` for the full risk parameter table.

### Hard Rules (Never Override)
1. **Max Drawdown**: If portfolio is down >10% from peak, stop all new trades
2. **Max Position Size**: Single position never exceeds 20% of sim portfolio
3. **Correlated Exposure**: Don't hold >3 correlated assets simultaneously
4. **Daily Loss Limit**: If daily PnL < -5%, pause trading for 24h

### Soft Rules (Override with HIGH confidence only)
1. **Volatility Check**: If 24h volatility > 5%, reduce position size by 50%
2. **Low Liquidity Warning**: If 24h volume < $500M, reduce position size by 30%
3. **News Risk**: If high-impact news pending (Fed meeting, halving), hold size flat

### Stop-Loss Calculation
```
Stop Loss = entry_price * (1 - risk_per_trade_pct)
# Default: risk_per_trade_pct = 0.02 (2%)

Take Profit = entry_price * (1 + reward_ratio * risk_per_trade_pct)
# Default: reward_ratio = 2.0 (2:1 R/R)
```

---

## Dashboard Output

After any full cycle, always print a clean dashboard. Use `scripts/dashboard.py` to generate it, or format inline:

```
╔══════════════════════════════════════════════════════╗
║           BITGET TRADING AGENT — DASHBOARD           ║
╠══════════════════════════════════════════════════════╣
║  Asset: BTC/USDT         Time: 2026-06-06 17:00 UTC  ║
╠══════════════════════════════════════════════════════╣
║  SIGNAL BREAKDOWN                                    ║
║  News Sentiment:    ████████░░  +6.4  BULLISH        ║
║  Technicals:        ██████░░░░  +4.2  BULLISH        ║
║  On-Chain:          ████░░░░░░  +3.1  NEUTRAL        ║
║  Macro:             ███░░░░░░░  +2.8  NEUTRAL        ║
║  ─────────────────────────────────────────────────   ║
║  Aggregate Score:   +5.8  →  DECISION: BUY 🟢        ║
║  Confidence:        MEDIUM                           ║
╠══════════════════════════════════════════════════════╣
║  TRADE EXECUTED (SIM)                                ║
║  Entry: $68,420   SL: $67,051   TP: $71,156          ║
║  Size: $100 USDT  Risk: 2%      R/R: 2:1             ║
╠══════════════════════════════════════════════════════╣
║  PORTFOLIO STATUS                                    ║
║  Total Sim Balance: $1,000 USDT                      ║
║  Open Positions: 1  |  Realized PnL: +$23.40         ║
║  Peak Balance: $1,023  |  Max Drawdown: -1.2%        ║
╚══════════════════════════════════════════════════════╝
```

---

## Backtest Mode

To replay historical decisions, use `scripts/backtest.py`:

```bash
python scripts/backtest.py \
  --asset BTC \
  --start 2026-05-01 \
  --end 2026-06-01 \
  --initial_capital 1000 \
  --output backtest_results.csv
```

The script:
1. Fetches historical OHLCV data from Bitget
2. Replays signal computation for each candle
3. Simulates trades based on decision engine output
4. Logs all trades to CSV and prints a summary

After backtesting, generate the Excel report:
```bash
python scripts/generate_report.py --input backtest_results.csv --output report.xlsx
```

---

## References

- `references/perception.md` — Full API endpoints, response schemas, parsing logic
- `references/decision.md` — Decision prompt templates and confidence calibration guide
- `references/risk.md` — Full risk parameter table and position sizing formulas

## Scripts

- `scripts/sim_trader.py` — Sim trade execution and log management
- `scripts/backtest.py` — Historical backtest runner
- `scripts/dashboard.py` — Terminal dashboard renderer
- `scripts/generate_report.py` — Excel/PDF report generator
- `scripts/fetch_signals.py` — Perception layer data fetcher

---

## Hackathon Submission Checklist

Before submitting to Bitget AI Hackathon S1 (deadline: June 25, 24:00 UTC+8):
- [ ] All 4 layers functional (perception, decision, execution, risk)
- [ ] At least 7 days of sim trade logs in `backtest_log.csv`
- [ ] Excel report generated from backtest results
- [ ] Dashboard screenshot captured
- [ ] GitHub repo with clean README
- [ ] Demo video (2-3 min) showing live agent cycle
- [ ] X/Twitter post tagged #BitgetHackathon for Community Award
