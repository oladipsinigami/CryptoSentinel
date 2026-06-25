# CryptoSentinel AI — Bitget AI Hackathon S1 (Track 1) Submission Description

**Word count target: ≤ 200 words**

---

**Final submission-ready version (196 words):**

CryptoSentinel AI is an autonomous, risk-disciplined crypto trading agent built for Bitget AI Hackathon Track 1. It solves the problem of fragmented, emotional decision-making in volatile markets with a complete closed-loop strategy:

• **Perception**: Dynamically scans top-volume USDT crypto pairs on Bitget (filtering out tokenized stocks). Computes RSI, MACD, Bollinger Bands, and EMA crossovers using the official Bitget technical-analysis library (kline_indicators.py). Gathers real-time market intelligence by calling the official Bitget Skill Hub MCP server (datahub.noxiaohao.com/mcp) — the same server used by all 5 Skill Hub skills — for sentiment_index, derivatives_sentiment (long/short ratios, taker ratios), crypto_market (global macro), and news_feed.

• **Decision**: Normalizes multi-source signals into a -10 to +10 aggregate score, mapped to BUY/SELL/HOLD with confidence levels and EMA trend filtering. Autonomously selects the highest-conviction opportunities across dozens of coins.

• **Execution & Risk**: Simulates leveraged paper trades with dynamic volatility-adjusted stops (2:1 R:R), 20% position cap, 3 max concurrent positions, 10% drawdown halt, and realistic 0.05% fees.

Validated via chronological backtests and live autonomous cycles. The interactive web dashboard with natural language chat serves as the public demo. All Bitget Skill Hub MCP tools are called directly — not just "mapped to."