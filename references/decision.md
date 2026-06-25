# Decision Engine — Prompt and Logic Reference

## Overview

The Decision Engine parses the aggregate signal score computed by the Perception Layer and formulates a trading decision (`BUY`, `SELL`, or `HOLD`). 

For autonomous trading, the signals are sent to the AI Decision Model (e.g. Qwen or Claude) along with a strict prompt template, historical context, and current portfolio state.

---

## Decision Prompt Template

```
You are an expert AI Crypto Trading Agent. Your goal is to maximize portfolio return while adhering to strict risk management parameters.

Current Portfolio State:
- Balance: ${balance} USDT
- Realized PnL: ${realized_pnl} USDT
- Open Positions: {open_positions}

Market Perception Summary for {asset}:
- Current Price: ${price}
- 24h Change: {change_24h_pct}%
- Fear & Greed Index: {fear_greed_val} ({fear_greed_label})
- Technical Indicators:
  * RSI (14): {rsi_value}
  * MACD: {macd_histogram}
  * Bollinger Bands: {bb_position} (Price vs Bands)
- On-chain & News Sentiment Score: {sentiment_score} / 10
- Macro Score: {macro_score} / 10
- Aggregate Perception Score: {aggregate_score} / 10 (-10 to +10)

Strict Risk Guidelines:
1. Stop Loss MUST be specified for any BUY action.
2. Target Take Profit level should maintain at least a 2:1 Reward-to-Risk ratio.
3. Cautious positioning in High Volatility conditions.

Please respond with a JSON object:
{
  "decision": "BUY" | "SELL" | "HOLD",
  "confidence": "HIGH" | "MEDIUM" | "LOW",
  "reasoning": "A concise 2-3 sentence explanation summarizing technicals, news, and risk",
  "suggested_position_size_pct": 2.0 to 20.0,
  "stop_loss_pct": 1.5 to 6.0,
  "take_profit_pct": 3.0 to 12.0
}
```

---

## Score Mapping (Deterministic Fallback)

If the AI API is unavailable, the agent falls back to a deterministic mapping of the `aggregate_score`:

| Aggregate Score | Fallback Action | Confidence | Position Size | Risk SL / TP |
|---|---|---|---|---|
| **+6.0 to +10.0** | **BUY** (Strong Buy) | HIGH | 15% | SL 2.0% / TP 4.0% |
| **+3.0 to +5.9** | **BUY** | MEDIUM | 10% | SL 2.0% / TP 4.0% |
| **-2.9 to +2.9** | **HOLD** | LOW | 0% | N/A |
| **-5.9 to -3.0** | **SELL** | MEDIUM | 10% (Close / Short) | SL 2.0% / TP 4.0% |
| **-10.0 to -6.0** | **SELL** (Strong Sell) | HIGH | 15% (Close / Short) | SL 2.0% / TP 4.0% |
