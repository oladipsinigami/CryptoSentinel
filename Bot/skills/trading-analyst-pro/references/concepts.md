# Trading Concepts Reference

A quick-reference glossary for ICT/SMC, Wyckoff, and Price Action concepts used by Trading Analyst Pro.

---

## ICT / Smart Money Concepts (SMC)

### Market Structure
- **Higher High (HH):** A swing high that exceeds the previous swing high — bullish structure
- **Higher Low (HL):** A swing low that is higher than the previous swing low — bullish continuation
- **Lower High (LH):** A swing high that is lower than the previous — bearish structure
- **Lower Low (LL):** A swing low that is lower than the previous — bearish continuation

### Break of Structure (BOS)
A continuation signal. Price breaks through a **swing point in the same direction as the current trend**.
- In an uptrend: price breaks above a previous HH → BOS bullish
- In a downtrend: price breaks below a previous LL → BOS bearish
- **Implication:** Trend is intact and likely to continue

### Change of Character (CHoCH)
A potential reversal signal. Price breaks through a **swing point in the opposite direction of the current trend** for the first time.
- In an uptrend: price breaks below a HL → CHoCH bearish
- In a downtrend: price breaks above a LH → CHoCH bullish
- **Implication:** Momentum is shifting; watch for new structure to form

### Order Block (OB)
The **last opposing candle(s)** before a strong, impulsive move away from a zone.
- **Bullish OB:** Last bearish candle (red) before a strong bullish impulse
- **Bearish OB:** Last bullish candle (green) before a strong bearish impulse
- **Entry logic:** Price returns to the OB zone, offering a high-probability reversal entry
- **Validity:** An OB is violated if price closes fully beyond it (not just wicks through)

### Fair Value Gap (FVG)
A 3-candle price imbalance where the middle candle's body creates a gap between candle 1's high and candle 3's low (bullish) or candle 1's low and candle 3's high (bearish).
- **Bullish FVG:** Candle 3's low is above candle 1's high — price may return to "fill" this area before continuing up
- **Bearish FVG:** Candle 3's high is below candle 1's low — price may return to fill before continuing down
- **Usage:** Acts as a magnet for price; also used as entry zones on retrace

### Liquidity
**Buy-side liquidity:** Resting stop orders above swing highs and equal highs — inducement for price to sweep up
**Sell-side liquidity:** Resting stop orders below swing lows and equal lows — inducement for price to sweep down
- **Liquidity sweep (stop hunt):** Price spikes into a liquidity pool, triggers stops, then reverses — this reversal is often the actual trade

### Premium vs. Discount
- **Premium:** Price is above the 50% retracement of a swing (0.5 Fibonacci level) — in an uptrend, this is where sells are likely; in a downtrend, this is where sells continue
- **Discount:** Price is below the 50% retracement — in a downtrend, where buys may be expected; in an uptrend, where buys continue
- **Rule:** Buy in discount, sell in premium (relative to the prevailing range)

### Draw on Liquidity (DOL)
The next objective that price is likely drawn toward — typically the nearest pool of liquidity (equal highs, session highs, previous day high/low, weekly levels).

### Supply and Demand Zones
- **Supply zone:** Origin of a strong bearish move; proximal edge (bottom of zone) is the entry reference for shorts
- **Demand zone:** Origin of a strong bullish move; proximal edge (top of zone) is the entry reference for longs
- **Key rule:** The zone is fresh (unused) when price has not returned to it since the original move

### Volume Imbalance
Similar to FVG but specifically when there is a visible gap in volume at a price level — often seen as literal price gaps. High probability of being revisited.

---

## Wyckoff Methodology

### Core Principle
"The market moves through cause and effect." Large operators (composite man) accumulate or distribute before significant moves. Retail participants provide the liquidity needed for these operations.

### Accumulation Schematic
1. **PS (Preliminary Support):** First attempt to stop a downtrend
2. **SC (Selling Climax):** Panic selling, high volume bottom
3. **AR (Automatic Rally):** Bounce from SC — defines the trading range
4. **ST (Secondary Test):** Retest of SC area, lower volume
5. **Spring:** Shakeout below the trading range low; traps latecomers short
6. **LPS (Last Point of Support):** Final low before markup; entry opportunity
7. **SOS (Sign of Strength):** Strong up-move confirming accumulation complete

### Distribution Schematic
Mirror of accumulation. Key events:
- **PSY (Preliminary Supply):** Initial resistance after uptrend
- **BC (Buying Climax):** Euphoric buying top
- **UTAD (Upthrust After Distribution):** False breakout above range — traps latecomers long
- **LPSY (Last Point of Supply):** Final weak rally before markdown

### Spring / Shakeout
Price temporarily breaks below support (or above resistance in an upthrust) with low volume then reverses. Signals the exhaustion of the prior trend and that the composite man has absorbed supply (spring) or demand (upthrust).

---

## Fibonacci Levels (Key SMC Confluences)

| Level | Usage |
|---|---|
| 0.236 | Shallow retracement in strong trend |
| 0.382 | Common swing trade entry in strong trend |
| 0.5 | Premium/discount midpoint |
| 0.618 | "Golden ratio" — strongest retracement level |
| 0.705 | ICT optimal trade entry zone |
| 0.79 | Deep retracement; often aligns with OBs |
| 1.0 | Previous swing (invalidation reference) |
| 1.272 / 1.618 | Extension targets (TP2/TP3 references) |

---

## Session Structure (Forex / Indices)

| Session | Time (UTC) | Characteristics |
|---|---|---|
| **Asian** | 00:00 – 08:00 | Low volatility, range-forming, liquidity resting |
| **London** | 07:00 – 12:00 | High volatility, often sets the daily direction |
| **New York** | 12:00 – 17:00 | Continuation or reversal of London move |
| **Overlap** | 12:00 – 15:00 | Highest volume and volatility of the day |

**Killzones (ICT):** 02:00–05:00 UTC (Asian KZ), 07:00–10:00 (London KZ), 13:00–16:00 (NY KZ) — highest probability ICT entry windows.

---

## Risk Assessment Criteria

### LOW Risk
- Setup has 4+ confluences
- Clear and wide stop loss placement beyond structure
- High liquidity environment, no major news pending
- RR ratio ≥ 1:3
- Trend and timeframes fully aligned

### MEDIUM Risk
- 2–3 confluences
- One timeframe conflicting or unclear
- Moderate news risk
- RR between 1:2 and 1:3

### HIGH Risk
- Single confluence
- Conflicting timeframes
- High-impact news pending within trade window
- Spread/slippage likely (pre-market, thin session)
- Ranging market with false breakout risk
