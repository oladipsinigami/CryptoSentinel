# Risk Management — Parameter Reference

## Default Risk Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `initial_capital` | 1000 USDT | Starting sim portfolio value |
| `risk_per_trade` | 2% | Max % of capital risked per trade |
| `reward_ratio` | 2.0 | Take-profit = risk × reward_ratio |
| `max_position_pct` | 20% | Max single position as % of portfolio |
| `max_drawdown_pct` | 10% | Stop trading if drawdown exceeds this |
| `daily_loss_limit` | 5% | Pause trading if daily loss exceeds this |
| `max_open_positions` | 3 | Max concurrent open positions |
| `high_volatility_threshold` | 5% | 24h move that triggers size reduction |

## Position Sizing Formula

```python
def calculate_position_size(capital, entry, stop_loss, risk_pct=0.02):
    risk_amount = capital * risk_pct
    risk_per_unit = abs(entry - stop_loss)
    units = risk_amount / risk_per_unit
    position_value = units * entry
    # Cap at max_position_pct
    max_value = capital * 0.20
    return min(position_value, max_value)
```

## Stop-Loss Levels by Asset Volatility

| Asset | Low Vol | Medium Vol | High Vol |
|-------|---------|------------|----------|
| BTC   | 1.5%    | 2.0%       | 3.0%     |
| ETH   | 2.0%    | 2.5%       | 4.0%     |
| ALT   | 3.0%    | 4.0%       | 6.0%     |

Volatility category: Low = 24h vol <2%, Medium = 2-5%, High = >5%

## Drawdown Tracking

```python
def check_drawdown(peak_balance, current_balance, limit=0.10):
    drawdown = (peak_balance - current_balance) / peak_balance
    if drawdown >= limit:
        return False  # HALT TRADING
    return True  # OK to trade
```

## Risk Override Messages

When a hard rule blocks a trade, log this message:
```
TRADE BLOCKED: [RULE_NAME]
Reason: [EXPLANATION]
Recommended action: HOLD
Next review: [TIMESTAMP + 24h if daily limit, else next cycle]
```
