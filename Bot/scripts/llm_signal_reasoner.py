import os
import json
import re
import urllib.request
import urllib.error
import logging

def parse_json_response(content: str) -> dict:
    """Parse JSON robustly from LLM response."""
    content = content.strip()
    try:
        return json.loads(content)
    except Exception:
        pass
    
    # Try regex extraction of anything between { and }
    try:
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception:
        pass
        
    return None

def call_qwen_api(api_key: str, prompt: str) -> dict:
    """Invoke Alibaba Cloud Qwen API via compatible OpenAI endpoint."""
    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    model = os.environ.get("BITGET_QWEN_MODEL", "qwen-plus")
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a professional quantitative cryptocurrency trader and risk manager. Respond ONLY with a valid JSON object matching the requested schema. No extra words, no markdown blocks."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            content = res_data["choices"][0]["message"]["content"].strip()
            return parse_json_response(content)
    except Exception as e:
        logging.error(f"[llm_signal_reasoner] Qwen API request failed: {e}")
        return None

def call_claude_api(api_key: str, prompt: str) -> dict:
    """Invoke Anthropic Claude API via messages endpoint."""
    url = "https://api.anthropic.com/v1/messages"
    model = os.environ.get("BITGET_CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
    
    payload = {
        "model": model,
        "max_tokens": 1000,
        "system": "You are a professional quantitative cryptocurrency trader and risk manager. Respond ONLY with a valid JSON object matching the requested schema. No extra words, no markdown blocks.",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }
    
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"
    }
    
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            content = res_data["content"][0]["text"].strip()
            return parse_json_response(content)
    except Exception as e:
        logging.error(f"[llm_signal_reasoner] Claude API request failed: {e}")
        return None

def rule_based_fallback(asset: str, price: float, technicals: dict, sentiment: dict, regime: str, strategy_intel: dict) -> dict:
    """Dynamic, insightful fallback reasoner when LLM is unavailable."""
    bullets = []
    
    # Check direction
    direction = "HOLD"
    strat_decision = strategy_intel.get("decision", "") if strategy_intel else ""
    if strat_decision:
        strat_dec_upper = str(strat_decision).upper()
        if "BUY" in strat_dec_upper or "LONG" in strat_dec_upper:
            direction = "LONG"
        elif "SELL" in strat_dec_upper or "SHORT" in strat_dec_upper:
            direction = "SHORT"
            
    # 1. EMA cross or structure
    ema_cross = technicals.get("ema_cross") if technicals else None
    if ema_cross == "bullish" or (direction == "LONG" and ema_cross != "bearish"):
        bullets.append("Price above 200 EMA")
    elif ema_cross == "bearish" or (direction == "SHORT" and ema_cross != "bullish"):
        bullets.append("Price below 200 EMA")
    else:
        bullets.append("Price consolidating around key EMAs")
        
    # 2. Momentum
    rsi = technicals.get("rsi") if technicals else None
    if direction == "LONG":
        if rsi is not None and rsi < 45:
            bullets.append("Bullish momentum (RSI oversold/rebound)")
        else:
            bullets.append("Bullish momentum")
    elif direction == "SHORT":
        if rsi is not None and rsi > 55:
            bullets.append("Bearish momentum (RSI overbought/rejection)")
        else:
            bullets.append("Bearish momentum")
    else:
        bullets.append("Neutral momentum")
        
    # 3. Fear & Greed
    fg_val = 50
    if sentiment:
        if isinstance(sentiment.get("fear_greed"), dict):
            fg_val = sentiment["fear_greed"].get("value", 50)
        else:
            fg_val = sentiment.get("value", 50)
    bullets.append(f"Fear & Greed = {fg_val}")
    
    # 4. Strategy or regime specificity (dynamic and insightful)
    strat_reason = strategy_intel.get("reasoning") if strategy_intel else None
    strat_name = strategy_intel.get("strategy") if strategy_intel else None
    if strat_reason and len(strat_reason) > 5:
        # extract first clause/sentence to keep it concise and punchy
        clean_reason = strat_reason.split(".")[0].strip()
        if "selected" not in clean_reason.lower() and "chosen" not in clean_reason.lower():
            bullets.append(clean_reason)
    elif strat_name:
        bullets.append(f"Strategy indicator trigger: {strat_name}")
        
    # Confidence and Risk
    conf_str = "MEDIUM"
    if strategy_intel:
        conf_str = strategy_intel.get("confidence", "MEDIUM").upper()
    
    if "HIGH" in conf_str:
        confidence_pct = 82
        risk_level = "Medium"
    elif "MEDIUM" in conf_str:
        confidence_pct = 65
        risk_level = "Medium"
    else:
        confidence_pct = 35
        risk_level = "High"
        
    return {
        "reasoning_bullets": bullets,
        "confidence_pct": confidence_pct,
        "risk_level": risk_level
    }

def generate_signal_report(asset, price, technicals, sentiment, regime, strategy_intel) -> str:
    """Unified signal reporter that formats inputs in exactly the requested structure."""
    sym = asset.upper().replace("USDT", "") + "USDT"
    
    # 1. Determine direction
    direction = "HOLD"
    strat_decision = strategy_intel.get("decision", "") if strategy_intel else ""
    if strat_decision:
        strat_dec_upper = str(strat_decision).upper()
        if "BUY" in strat_dec_upper or "LONG" in strat_dec_upper:
            direction = "LONG"
        elif "SELL" in strat_dec_upper or "SHORT" in strat_dec_upper:
            direction = "SHORT"
    else:
        # Fallback if no strategy decision
        tech_score = technicals.get("score", 0) if technicals else 0
        direction = "LONG" if tech_score >= 0 else "SHORT"
        
    # 2. Entry, TP, SL display
    entry_val = strategy_intel.get("entry_price") if strategy_intel else None
    tp_val = strategy_intel.get("take_profit") if strategy_intel else None
    sl_val = strategy_intel.get("stop_loss") if strategy_intel else None
    
    if entry_val is None or entry_val <= 0:
        entry_val = price
        
    # If tp/sl are missing, calculate based on standard 2% bounds
    if tp_val is None or tp_val <= 0 or sl_val is None or sl_val <= 0:
        sl_pct = 0.02
        if "BTC" in sym:
            sl_pct = 0.015
        elif "ETH" in sym:
            sl_pct = 0.02
        else:
            sl_pct = 0.04
            
        if direction == "SHORT":
            tp_val = entry_val * (1.0 - sl_pct * 2.0)
            sl_val = entry_val * (1.0 + sl_pct)
        else:
            tp_val = entry_val * (1.0 + sl_pct * 2.0)
            sl_val = entry_val * (1.0 - sl_pct)

    # Format prices
    def fmt_price(val):
        if val >= 1000:
            return f"{val:,.0f}"
        elif val >= 1:
            return f"{val:,.2f}"
        else:
            return f"{val:,.4f}"
            
    entry_display = fmt_price(entry_val)
    tp_display = fmt_price(tp_val)
    sl_display = fmt_price(sl_val)
    
    # 3. Strategy Used
    strat_name = strategy_intel.get("strategy") if strategy_intel else None
    strat_used = strat_name if (strat_name and strat_name != "None") else "Trend Following"
    
    # 4. Try calling LLM (Qwen or Claude)
    result = None
    qwen_key = os.environ.get("BITGET_QWEN_API_KEY") or os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("QWEN_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    
    prompt = f"""
We have the following market intelligence data for {sym}:
Asset: {sym}
Price: {price}
Technicals: {json.dumps(technicals)}
Sentiment: {json.dumps(sentiment)}
Regime: {json.dumps(regime)}
Strategy Intelligence: {json.dumps(strategy_intel)}

Please analyze this data and generate:
1. 3 to 4 detailed, professional, and highly insightful bullet points justifying a trade decision (LONG, SHORT, or HOLD). Do not use generic statements like 'Bullish momentum' without context. Refer to the actual values where appropriate (e.g. price, RSI, Fear & Greed).
2. A confidence percentage (integer between 0 and 100).
3. A risk level ('Low', 'Medium', or 'High').

Your response must be a JSON object matching this schema exactly:
{{
  "reasoning_bullets": [
    "bullet point 1",
    "bullet point 2",
    "bullet point 3"
  ],
  "confidence_pct": 82,
  "risk_level": "Medium"
}}

Respond ONLY with the JSON object. Do not include markdown headers or text outside the JSON.
"""

    if qwen_key:
        result = call_qwen_api(qwen_key, prompt)
    elif anthropic_key:
        result = call_claude_api(anthropic_key, prompt)
        
    # If API keys are missing or API calls fail, run rule-based fallback
    if not result:
        result = rule_based_fallback(sym, price, technicals, sentiment, regime, strategy_intel)
        
    bullets = result.get("reasoning_bullets", [])
    confidence_pct = result.get("confidence_pct", 50)
    risk_level = result.get("risk_level", "Medium")
    
    # Clean reasoning bullets format and deduplicate
    def is_duplicate_or_similar(new_bullet, existing_list):
        new_words = set(re.findall(r'\w+', new_bullet.lower()))
        if not new_words:
            return True
        for ext in existing_list:
            # strip leading bullet
            ext_text = ext[2:] if ext.startswith("• ") else ext
            ext_words = set(re.findall(r'\w+', ext_text.lower()))
            if not ext_words:
                continue
            intersection = new_words.intersection(ext_words)
            smaller_len = min(len(new_words), len(ext_words))
            if len(intersection) / smaller_len >= 0.7:
                return True
        return False

    cleaned_bullets = []
    for b in bullets:
        clean_b = b.strip()
        if clean_b.startswith("•") or clean_b.startswith("-") or clean_b.startswith("*"):
            clean_b = clean_b[1:].strip()
        if not clean_b:
            continue
        if not is_duplicate_or_similar(clean_b, cleaned_bullets):
            cleaned_bullets.append(f"• {clean_b}")
            
    reason_display = "\n".join(cleaned_bullets)
    
    # 5. Format final message string
    full_message = (
        f"Signal: {direction} {sym}\n"
        f"Entry: {entry_display}\n"
        f"Take Profit: {tp_display}\n"
        f"Stop Loss: {sl_display}\n"
        f"Strategy Used: {strat_used}\n"
        f"Reason:\n"
        f"{reason_display}\n"
        f"Confidence: {confidence_pct}%\n"
        f"Risk Level: {risk_level}"
    )
    
    return full_message
