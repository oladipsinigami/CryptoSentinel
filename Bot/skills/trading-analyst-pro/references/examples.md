# Trading Analyst Pro — Example Inputs & Outputs

These examples show how the skill handles different types of user input across asset classes and trading styles.

---

## Example 1: Forex Intraday — ICT Setup (EUR/USD)

**User input:**
> "EURUSD 4H is in a clear uptrend making HH/HL. Price just swept the 1.0820 equal lows during London and I'm seeing a 15m bullish CHoCH at 1.0835. There's an OB from 1.0825–1.0840 from the last impulse. RSI on 15m just crossed back above 50. What's your read?"

**Expected output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 TRADING ANALYST PRO — SIGNAL REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Asset:          EUR/USD
Timeframe:      15M (Bias: 4H)
Trade Type:     Intraday
Market Type:    Trending (Bullish)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MARKET BIAS:    🟢 BULLISH
CONFIDENCE:     82%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TRADE SETUP
───────────
Direction:      LONG
Entry Zone:     1.0825 – 1.0840 (Bullish OB — enter on 15m bullish engulfing or rejection wick within zone)
Stop Loss:      1.0813 — below the liquidity sweep extreme (equal lows wick)
Take Profit 1:  1.0870 — next minor resistance / 1:2 RR
Take Profit 2:  1.0910 — prior 4H swing high
Take Profit 3:  1.0955 — HTF draw on liquidity / previous week high

Risk/Reward:    1:2.2 (to TP1) | 1:4.2 (to TP2) | 1:6.8 (to TP3)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REASONING
───────────
• 4H market structure is bullish (HH/HL intact) — HTF bias confirmed
• Liquidity sweep of equal lows at 1.0820 during London open — classic stop hunt before continuation
• 15M CHoCH confirms institutional entry; smart money absorbed sell-side liquidity
• Price returning into a clean OB (1.0825–1.0840) with RSI momentum recovery above 50

INVALIDATION CONDITIONS
───────────────────────
• 15M candle closes below 1.0813 (below the sweep wick) — invalidates the entire reversal
• 4H candle closes below the most recent 4H HL — bullish structure broken

RISK ASSESSMENT:  🟢 LOW
Strong confluence of 4+ factors. Clean structure. London session timing optimal.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  DISCLAIMER: This is analytical output, not financial advice.
    Always apply your own risk management rules.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Example 2: Crypto Scalp — BTC (Ranging Market)

**User input:**
> "BTC has been stuck between 67,200 and 68,800 for the last 12 hours. No clear direction. 1H candles look messy. Should I trade this?"

**Expected output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 TRADING ANALYST PRO — SIGNAL REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Asset:       BTC/USD
Confidence:  28%

⛔ NO TRADE

Reason:
• Market is in a clear range (67,200–68,800) with no directional bias — no tradeable structure
• 1H price action is choppy, meaning any OB or FVG identified would have low reliability
• No liquidity sweep on either side yet — the range has not been "solved" by the market

What to watch for:
• A sweep of 67,200 with an immediate recovery and 15M CHoCH bullish → potential long back toward 68,800
• A sweep of 68,800 with rejection and 15M CHoCH bearish → potential short back toward 67,200
• A clean BOS above 68,800 on 1H close with volume → breakout long toward 70,000
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Example 3: Indices Swing Trade — US30 (Wyckoff Context)

**User input:**
> "US30 on the daily has been ranging for 3 weeks between 38,500 and 39,800. Last week we had a sharp drop to 38,300 on high volume that immediately bounced back into the range. Daily RSI is at 45 and there's a series of compression candles. Feels like accumulation to me."

**Expected output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 TRADING ANALYST PRO — SIGNAL REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Asset:          US30 (Dow Jones)
Timeframe:      Daily (Bias: Weekly)
Trade Type:     Swing
Market Type:    Transitional → Wyckoff Accumulation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MARKET BIAS:    🟢 BULLISH (Developing)
CONFIDENCE:     63%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TRADE SETUP
───────────
Direction:      LONG (reduced size — accumulation not confirmed)
Entry Zone:     38,500 – 38,700 (Demand zone / Wyckoff SC area — enter on 4H bullish CHoCH)
Stop Loss:      38,150 — below the spring extreme at 38,300 with buffer
Take Profit 1:  39,200 — midpoint of range / LPS area
Take Profit 2:  39,800 — top of range resistance
Take Profit 3:  41,200 — HTF liquidity target above prior weekly high

Risk/Reward:    1:2.0 (to TP1) | 1:3.7 (to TP2) | 1:8.5 (to TP3)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REASONING
───────────
• 3-week trading range is consistent with Wyckoff accumulation schematic
• Sharp drop to 38,300 with immediate recovery is characteristic of a Spring — shakeout of weak longs
• High volume on the spring followed by compression (lower volume) suggests absorption complete
• Daily RSI at 45 — room to run; not overbought

INVALIDATION CONDITIONS
───────────────────────
• Daily close below 38,150 — spring failed; downtrend continuation likely
• Sustained move below 38,300 without recovery within 1–2 sessions

RISK ASSESSMENT:  🟡 MEDIUM
Wyckoff setup is promising but accumulation not fully confirmed (no SOS yet). Position sizing
recommended at 50% of normal. Upgrade to full size on confirmed Sign of Strength (SOS) above 39,000.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  DISCLAIMER: This is analytical output, not financial advice.
    Always apply your own risk management rules.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Example 4: Stock — Earnings / News Risk

**User input:**
> "AAPL is at 187. Earnings are tomorrow after close. Should I enter a long now? It looks strong technically."

**Expected output snippet:**

> **RISK ASSESSMENT: 🔴 HIGH**
> High-impact earnings event tomorrow after close makes any technical setup unreliable. Price can gap 5–10% in either direction regardless of prior structure. This is not a technical analysis problem — it is a binary event risk problem.
>
> Recommendation: **Wait for post-earnings price action.** If AAPL gaps up and holds above 190, then reassess for a continuation long. If it gaps down and creates a demand zone, reassess for a counter-trend bounce. Do not carry a directional position into a binary event without hedging.

---

## Example 5: Missing Information

**User input:**
> "Is gold bullish right now?"

**Expected output:**

> I need a bit more to give you a quality read on Gold. Specifically:
>
> 1. **What timeframe are you trading?** (Scalp, intraday, swing, or position)
> 2. **What's the current price and the most recent swing high/low you can see?**
> 3. **Any recent price action you've noticed** — has it been making higher highs, sweeping a level, ranging?
>
> With those details I can give you a structured bias read and setup. Right now I'd just be guessing.
