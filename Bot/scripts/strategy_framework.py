#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Professional Multi-Strategy Trading Framework — CryptoSentinel AI
Features 24 strategies across 7 categories, market regime detection,
dynamic scoring, strategy selection, and performance tracking.
"""

import numpy as np
import pandas as pd
import os
import json
from typing import Dict, List, Tuple, Any, Optional

# === Base Strategy Class ===
class BaseStrategy:
    def __init__(self, name: str, category: str):
        self.name = name
        self.category = category  # e.g., 'Trend Following', 'Momentum', 'Mean Reversion', etc.

    def generate_signal(self, df: pd.DataFrame, atr: pd.Series) -> Dict[str, Any]:
        """
        Generate trade signal.
        Returns:
            {
                'signal': 1 (BUY), -1 (SELL), 0 (HOLD),
                'confidence': float (0.0 to 1.0),
                'entry_price': float,
                'stop_loss': float,
                'take_profit': float,
                'reasoning': str
            }
        """
        raise NotImplementedError

# === Utility Functions for Calculations ===
def get_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df['high']
    low = df['low']
    close = df['close']
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()

def get_ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def get_sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period, min_periods=1).mean()

# === Category 1: Trend Following ===

class EMACrossStrategy(BaseStrategy):
    def __init__(self, fast_period: int = 9, slow_period: int = 21):
        super().__init__("EMA Cross", "Trend Following")
        self.fast_period = fast_period
        self.slow_period = slow_period

    def generate_signal(self, df: pd.DataFrame, atr: pd.Series) -> Dict[str, Any]:
        if len(df) < self.slow_period:
            return {"signal": 0, "confidence": 0.0, "reasoning": "Insufficient data"}
        
        close = df['close']
        ema_fast = get_ema(close, self.fast_period)
        ema_slow = get_ema(close, self.slow_period)
        
        last_fast, prev_fast = ema_fast.iloc[-1], ema_fast.iloc[-2]
        last_slow, prev_slow = ema_slow.iloc[-1], ema_slow.iloc[-2]
        
        signal = 0
        confidence = 0.0
        reasoning = "EMA lines are parallel or neutral."
        
        # Golden Cross
        if prev_fast <= prev_slow and last_fast > last_slow:
            signal = 1
            # Confidence based on slope strength
            slope = (last_fast - prev_fast) / last_fast
            confidence = min(0.9, max(0.4, 0.5 + slope * 100))
            reasoning = f"EMA {self.fast_period} crossed above EMA {self.slow_period} (Golden Cross)."
        # Death Cross
        elif prev_fast >= prev_slow and last_fast < last_slow:
            signal = -1
            slope = (prev_fast - last_fast) / last_fast
            confidence = min(0.9, max(0.4, 0.5 + slope * 100))
            reasoning = f"EMA {self.fast_period} crossed below EMA {self.slow_period} (Death Cross)."
            
        entry_price = float(close.iloc[-1])
        stop_dist = 2 * float(atr.iloc[-1])
        
        return {
            "signal": signal,
            "confidence": round(confidence, 3),
            "entry_price": entry_price,
            "stop_loss": round(entry_price - stop_dist if signal == 1 else entry_price + stop_dist, 2),
            "take_profit": round(entry_price + 2 * stop_dist if signal == 1 else entry_price - 2 * stop_dist, 2),
            "reasoning": reasoning
        }

class SMACrossStrategy(BaseStrategy):
    def __init__(self, fast_period: int = 20, slow_period: int = 50):
        super().__init__("SMA Cross", "Trend Following")
        self.fast_period = fast_period
        self.slow_period = slow_period

    def generate_signal(self, df: pd.DataFrame, atr: pd.Series) -> Dict[str, Any]:
        if len(df) < self.slow_period:
            return {"signal": 0, "confidence": 0.0, "reasoning": "Insufficient data"}
            
        close = df['close']
        sma_fast = get_sma(close, self.fast_period)
        sma_slow = get_sma(close, self.slow_period)
        
        last_fast, prev_fast = sma_fast.iloc[-1], sma_fast.iloc[-2]
        last_slow, prev_slow = sma_slow.iloc[-1], sma_slow.iloc[-2]
        
        signal = 0
        confidence = 0.0
        reasoning = "SMA trend is flat."
        
        if prev_fast <= prev_slow and last_fast > last_slow:
            signal = 1
            confidence = 0.65
            reasoning = f"SMA {self.fast_period} crossed above SMA {self.slow_period}."
        elif prev_fast >= prev_slow and last_fast < last_slow:
            signal = -1
            confidence = 0.65
            reasoning = f"SMA {self.fast_period} crossed below SMA {self.slow_period}."
            
        entry_price = float(close.iloc[-1])
        stop_dist = 2 * float(atr.iloc[-1])
        
        return {
            "signal": signal,
            "confidence": confidence,
            "entry_price": entry_price,
            "stop_loss": round(entry_price - stop_dist if signal == 1 else entry_price + stop_dist, 2),
            "take_profit": round(entry_price + 2 * stop_dist if signal == 1 else entry_price - 2 * stop_dist, 2),
            "reasoning": reasoning
        }

class SupertrendStrategy(BaseStrategy):
    def __init__(self, period: int = 10, multiplier: float = 3.0):
        super().__init__("Supertrend", "Trend Following")
        self.period = period
        self.multiplier = multiplier

    def generate_signal(self, df: pd.DataFrame, atr: pd.Series) -> Dict[str, Any]:
        if len(df) < self.period:
            return {"signal": 0, "confidence": 0.0, "reasoning": "Insufficient data"}
            
        high = df['high']
        low = df['low']
        close = df['close']
        
        hl2 = (high + low) / 2
        basic_upper = hl2 + self.multiplier * atr
        basic_lower = hl2 - self.multiplier * atr
        
        n = len(df)
        upper_band = np.zeros(n)
        lower_band = np.zeros(n)
        direction = np.ones(n)
        
        upper_band[0] = basic_upper.iloc[0]
        lower_band[0] = basic_lower.iloc[0]
        
        for i in range(1, n):
            bu = basic_upper.iloc[i]
            bl = basic_lower.iloc[i]
            c = close.iloc[i]
            pc = close.iloc[i-1]
            
            upper_band[i] = bu if bu < upper_band[i-1] or pc > upper_band[i-1] else upper_band[i-1]
            lower_band[i] = bl if bl > lower_band[i-1] or pc < lower_band[i-1] else lower_band[i-1]
            
            if direction[i-1] == 1:
                direction[i] = -1 if c < lower_band[i] else 1
            else:
                direction[i] = 1 if c > upper_band[i] else -1
                
        last_dir = direction[-1]
        prev_dir = direction[-2]
        
        signal = 0
        confidence = 0.0
        reasoning = "Supertrend trend continues."
        
        if prev_dir == -1 and last_dir == 1:
            signal = 1
            confidence = 0.75
            reasoning = "Supertrend flipped bullish."
        elif prev_dir == 1 and last_dir == -1:
            signal = -1
            confidence = 0.75
            reasoning = "Supertrend flipped bearish."
            
        entry_price = float(close.iloc[-1])
        stop_dist = 2 * float(atr.iloc[-1])
        
        return {
            "signal": signal,
            "confidence": confidence,
            "entry_price": entry_price,
            "stop_loss": round(entry_price - stop_dist if signal == 1 else entry_price + stop_dist, 2),
            "take_profit": round(entry_price + 2 * stop_dist if signal == 1 else entry_price - 2 * stop_dist, 2),
            "reasoning": reasoning
        }

class ADXTrendStrategy(BaseStrategy):
    def __init__(self, period: int = 14):
        super().__init__("ADX Trend Strength", "Trend Following")
        self.period = period

    def generate_signal(self, df: pd.DataFrame, atr: pd.Series) -> Dict[str, Any]:
        if len(df) < self.period * 2:
            return {"signal": 0, "confidence": 0.0, "reasoning": "Insufficient data"}
            
        high = df['high']
        low = df['low']
        close = df['close']
        
        # DI+ / DI-
        up_move = high.diff()
        down_move = -low.diff()
        
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
        
        # Smoothed
        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs()
        ], axis=1).max(axis=1)
        
        atr_sum = tr.rolling(window=self.period).sum()
        plus_di = 100 * pd.Series(plus_dm).rolling(window=self.period).sum() / (atr_sum + 1e-10)
        minus_di = 100 * pd.Series(minus_dm).rolling(window=self.period).sum() / (atr_sum + 1e-10)
        
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-10)
        adx = dx.rolling(window=self.period).mean()
        
        last_adx = adx.iloc[-1]
        last_plus_di = plus_di.iloc[-1]
        last_minus_di = minus_di.iloc[-1]
        
        signal = 0
        confidence = 0.0
        reasoning = f"ADX is {last_adx:.1f} (Trend is weak or ranging)."
        
        if last_adx > 25:
            # Golden cross of DI+ / DI-
            if plus_di.iloc[-2] <= minus_di.iloc[-2] and last_plus_di > last_minus_di:
                signal = 1
                confidence = min(0.9, last_adx / 100.0)
                reasoning = f"ADX is {last_adx:.1f} (Strong Trend) with DI+ crossing above DI-."
            elif plus_di.iloc[-2] >= minus_di.iloc[-2] and last_plus_di < last_minus_di:
                signal = -1
                confidence = min(0.9, last_adx / 100.0)
                reasoning = f"ADX is {last_adx:.1f} (Strong Trend) with DI- crossing above DI+."
                
        entry_price = float(close.iloc[-1])
        stop_dist = 2 * float(atr.iloc[-1])
        
        return {
            "signal": signal,
            "confidence": round(confidence, 3),
            "entry_price": entry_price,
            "stop_loss": round(entry_price - stop_dist if signal == 1 else entry_price + stop_dist, 2),
            "take_profit": round(entry_price + 2 * stop_dist if signal == 1 else entry_price - 2 * stop_dist, 2),
            "reasoning": reasoning
        }

# === Category 2: Momentum ===

class MACDMomentumStrategy(BaseStrategy):
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        super().__init__("MACD Momentum", "Momentum")
        self.fast = fast
        self.slow = slow
        self.signal_p = signal

    def generate_signal(self, df: pd.DataFrame, atr: pd.Series) -> Dict[str, Any]:
        if len(df) < self.slow:
            return {"signal": 0, "confidence": 0.0, "reasoning": "Insufficient data"}
            
        close = df['close']
        ema_fast = get_ema(close, self.fast)
        ema_slow = get_ema(close, self.slow)
        dif = ema_fast - ema_slow
        dea = get_ema(dif, self.signal_p)
        hist = dif - dea
        
        last_dif, prev_dif = dif.iloc[-1], dif.iloc[-2]
        last_dea, prev_dea = dea.iloc[-1], dea.iloc[-2]
        
        signal = 0
        confidence = 0.0
        reasoning = "MACD momentum is flat."
        
        # Bullish golden cross below zero line
        if prev_dif <= prev_dea and last_dif > last_dea and last_dif < 0:
            signal = 1
            confidence = min(0.85, 0.5 + abs(hist.iloc[-1]) * 10)
            reasoning = "MACD golden cross occurred below the zero line (strong momentum shift)."
        # Bearish death cross above zero line
        elif prev_dif >= prev_dea and last_dif < last_dea and last_dif > 0:
            signal = -1
            confidence = min(0.85, 0.5 + abs(hist.iloc[-1]) * 10)
            reasoning = "MACD death cross occurred above the zero line (strong momentum shift)."
            
        entry_price = float(close.iloc[-1])
        stop_dist = 2 * float(atr.iloc[-1])
        
        return {
            "signal": signal,
            "confidence": round(confidence, 3),
            "entry_price": entry_price,
            "stop_loss": round(entry_price - stop_dist if signal == 1 else entry_price + stop_dist, 2),
            "take_profit": round(entry_price + 2 * stop_dist if signal == 1 else entry_price - 2 * stop_dist, 2),
            "reasoning": reasoning
        }

class RSIMomentumStrategy(BaseStrategy):
    def __init__(self, period: int = 14):
        super().__init__("RSI Momentum", "Momentum")
        self.period = period

    def generate_signal(self, df: pd.DataFrame, atr: pd.Series) -> Dict[str, Any]:
        if len(df) < self.period + 1:
            return {"signal": 0, "confidence": 0.0, "reasoning": "Insufficient data"}
            
        close = df['close']
        delta = close.diff()
        gain = np.where(delta > 0, delta, 0.0)
        loss = np.where(delta < 0, -delta, 0.0)
        
        avg_gain = pd.Series(gain).ewm(alpha=1/self.period, adjust=False).mean()
        avg_loss = pd.Series(loss).ewm(alpha=1/self.period, adjust=False).mean()
        
        rs = avg_gain / (avg_loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        
        last_rsi = rsi.iloc[-1]
        prev_rsi = rsi.iloc[-2]
        
        signal = 0
        confidence = 0.0
        reasoning = f"RSI is at {last_rsi:.1f} (Neutral momentum)."
        
        # Bullish cross above 50
        if prev_rsi <= 50 and last_rsi > 50:
            signal = 1
            confidence = min(0.8, 0.5 + (last_rsi - 50) / 50)
            reasoning = "RSI crossed above 50, indicating bullish momentum acceleration."
        # Bearish cross below 50
        elif prev_rsi >= 50 and last_rsi < 50:
            signal = -1
            confidence = min(0.8, 0.5 + (50 - last_rsi) / 50)
            reasoning = "RSI crossed below 50, indicating bearish momentum acceleration."
            
        entry_price = float(close.iloc[-1])
        stop_dist = 2 * float(atr.iloc[-1])
        
        return {
            "signal": signal,
            "confidence": round(confidence, 3),
            "entry_price": entry_price,
            "stop_loss": round(entry_price - stop_dist if signal == 1 else entry_price + stop_dist, 2),
            "take_profit": round(entry_price + 2 * stop_dist if signal == 1 else entry_price - 2 * stop_dist, 2),
            "reasoning": reasoning
        }

class StochasticMomentumStrategy(BaseStrategy):
    def __init__(self, period: int = 9, k_period: int = 3, d_period: int = 3):
        super().__init__("Stochastic Momentum", "Momentum")
        self.period = period
        self.k_period = k_period
        self.d_period = d_period

    def generate_signal(self, df: pd.DataFrame, atr: pd.Series) -> Dict[str, Any]:
        if len(df) < self.period + self.k_period + self.d_period:
            return {"signal": 0, "confidence": 0.0, "reasoning": "Insufficient data"}
            
        high = df['high']
        low = df['low']
        close = df['close']
        
        lowest_low = low.rolling(window=self.period).min()
        highest_high = high.rolling(window=self.period).max()
        
        rsv = 100 * (close - lowest_low) / (highest_high - lowest_low + 1e-10)
        
        k = rsv.rolling(window=self.k_period).mean()
        d = k.rolling(window=self.d_period).mean()
        
        last_k, prev_k = k.iloc[-1], k.iloc[-2]
        last_d, prev_d = d.iloc[-1], d.iloc[-2]
        
        signal = 0
        confidence = 0.0
        reasoning = f"Stochastic K={last_k:.1f}, D={last_d:.1f} (Neutral zone)."
        
        # Bullish golden cross in oversold zone (<20)
        if prev_k <= prev_d and last_k > last_d and last_k < 20:
            signal = 1
            confidence = min(0.85, 0.5 + (20 - last_k) / 40)
            reasoning = "Stochastic K crossed above D in the oversold zone (<20)."
        # Bearish death cross in overbought zone (>80)
        elif prev_k >= prev_d and last_k < last_d and last_k > 80:
            signal = -1
            confidence = min(0.85, 0.5 + (last_k - 80) / 40)
            reasoning = "Stochastic K crossed below D in the overbought zone (>80)."
            
        entry_price = float(close.iloc[-1])
        stop_dist = 2 * float(atr.iloc[-1])
        
        return {
            "signal": signal,
            "confidence": round(confidence, 3),
            "entry_price": entry_price,
            "stop_loss": round(entry_price - stop_dist if signal == 1 else entry_price + stop_dist, 2),
            "take_profit": round(entry_price + 2 * stop_dist if signal == 1 else entry_price - 2 * stop_dist, 2),
            "reasoning": reasoning
        }

class ROCMomentumStrategy(BaseStrategy):
    def __init__(self, period: int = 12, threshold: float = 2.0):
        super().__init__("Rate of Change (ROC)", "Momentum")
        self.period = period
        self.threshold = threshold

    def generate_signal(self, df: pd.DataFrame, atr: pd.Series) -> Dict[str, Any]:
        if len(df) < self.period + 1:
            return {"signal": 0, "confidence": 0.0, "reasoning": "Insufficient data"}
            
        close = df['close']
        roc = 100 * (close - close.shift(self.period)) / (close.shift(self.period) + 1e-10)
        
        last_roc = roc.iloc[-1]
        prev_roc = roc.iloc[-2]
        
        signal = 0
        confidence = 0.0
        reasoning = f"Rate of Change (ROC) is {last_roc:.2f}% (Below threshold of {self.threshold}%)."
        
        # Bullish acceleration
        if prev_roc <= self.threshold and last_roc > self.threshold:
            signal = 1
            confidence = min(0.8, abs(last_roc) / 10.0)
            reasoning = f"ROC crossed above the momentum threshold of {self.threshold}%."
        # Bearish acceleration
        elif prev_roc >= -self.threshold and last_roc < -self.threshold:
            signal = -1
            confidence = min(0.8, abs(last_roc) / 10.0)
            reasoning = f"ROC crossed below the momentum threshold of -{self.threshold}%."
            
        entry_price = float(close.iloc[-1])
        stop_dist = 2 * float(atr.iloc[-1])
        
        return {
            "signal": signal,
            "confidence": round(confidence, 3),
            "entry_price": entry_price,
            "stop_loss": round(entry_price - stop_dist if signal == 1 else entry_price + stop_dist, 2),
            "take_profit": round(entry_price + 2 * stop_dist if signal == 1 else entry_price - 2 * stop_dist, 2),
            "reasoning": reasoning
        }

# === Category 3: Mean Reversion ===

class BollingerBandsReversionStrategy(BaseStrategy):
    def __init__(self, period: int = 20, num_std: float = 2.0):
        super().__init__("Bollinger Band Reversion", "Mean Reversion")
        self.period = period
        self.num_std = num_std

    def generate_signal(self, df: pd.DataFrame, atr: pd.Series) -> Dict[str, Any]:
        if len(df) < self.period:
            return {"signal": 0, "confidence": 0.0, "reasoning": "Insufficient data"}
            
        close = df['close']
        sma = get_sma(close, self.period)
        std = close.rolling(window=self.period).std()
        
        upper_band = sma + self.num_std * std
        lower_band = sma - self.num_std * std
        
        last_price = close.iloc[-1]
        prev_price = close.iloc[-2]
        
        signal = 0
        confidence = 0.0
        reasoning = "Price is inside Bollinger Bands."
        
        # Oversold - Price went below lower band and closed back inside
        if prev_price < lower_band.iloc[-2] and last_price >= lower_band.iloc[-1]:
            signal = 1
            confidence = 0.7
            reasoning = "Price closed back inside the Lower Bollinger Band, indicating a mean reversion signal."
        # Overbought - Price went above upper band and closed back inside
        elif prev_price > upper_band.iloc[-2] and last_price <= upper_band.iloc[-1]:
            signal = -1
            confidence = 0.7
            reasoning = "Price closed back inside the Upper Bollinger Band, indicating a mean reversion signal."
            
        entry_price = float(last_price)
        stop_dist = 1.5 * float(atr.iloc[-1])
        
        return {
            "signal": signal,
            "confidence": confidence,
            "entry_price": entry_price,
            "stop_loss": round(entry_price - stop_dist if signal == 1 else entry_price + stop_dist, 2),
            "take_profit": round(entry_price + 2 * stop_dist if signal == 1 else entry_price - 2 * stop_dist, 2),
            "reasoning": reasoning
        }

class RSIReversionStrategy(BaseStrategy):
    def __init__(self, period: int = 14, overbought: float = 75.0, oversold: float = 25.0):
        super().__init__("RSI Reversion", "Mean Reversion")
        self.period = period
        self.overbought = overbought
        self.oversold = oversold

    def generate_signal(self, df: pd.DataFrame, atr: pd.Series) -> Dict[str, Any]:
        if len(df) < self.period + 1:
            return {"signal": 0, "confidence": 0.0, "reasoning": "Insufficient data"}
            
        close = df['close']
        delta = close.diff()
        gain = np.where(delta > 0, delta, 0.0)
        loss = np.where(delta < 0, -delta, 0.0)
        
        avg_gain = pd.Series(gain).ewm(alpha=1/self.period, adjust=False).mean()
        avg_loss = pd.Series(loss).ewm(alpha=1/self.period, adjust=False).mean()
        
        rs = avg_gain / (avg_loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        
        last_rsi = rsi.iloc[-1]
        prev_rsi = rsi.iloc[-2]
        
        signal = 0
        confidence = 0.0
        reasoning = f"RSI is {last_rsi:.1f} (No reversion extremes)."
        
        # Bullish reversal (RSI crosses back above oversold)
        if prev_rsi <= self.oversold and last_rsi > self.oversold:
            signal = 1
            confidence = min(0.9, 0.5 + (50 - last_rsi) / 50)
            reasoning = f"RSI was oversold at {prev_rsi:.1f} and has begun reclaiming the oversold boundary."
        # Bearish reversal (RSI crosses back below overbought)
        elif prev_rsi >= self.overbought and last_rsi < self.overbought:
            signal = -1
            confidence = min(0.9, 0.5 + (last_rsi - 50) / 50)
            reasoning = f"RSI was overbought at {prev_rsi:.1f} and has begun breaking below the overbought boundary."
            
        entry_price = float(close.iloc[-1])
        stop_dist = 1.5 * float(atr.iloc[-1])
        
        return {
            "signal": signal,
            "confidence": round(confidence, 3),
            "entry_price": entry_price,
            "stop_loss": round(entry_price - stop_dist if signal == 1 else entry_price + stop_dist, 2),
            "take_profit": round(entry_price + 2 * stop_dist if signal == 1 else entry_price - 2 * stop_dist, 2),
            "reasoning": reasoning
        }

class ZScoreReversionStrategy(BaseStrategy):
    def __init__(self, period: int = 20, z_threshold: float = 2.0):
        super().__init__("Z-Score Reversion", "Mean Reversion")
        self.period = period
        self.z_threshold = z_threshold

    def generate_signal(self, df: pd.DataFrame, atr: pd.Series) -> Dict[str, Any]:
        if len(df) < self.period:
            return {"signal": 0, "confidence": 0.0, "reasoning": "Insufficient data"}
            
        close = df['close']
        sma = get_sma(close, self.period)
        std = close.rolling(window=self.period).std()
        z_score = (close - sma) / (std + 1e-10)
        
        last_z = z_score.iloc[-1]
        prev_z = z_score.iloc[-2]
        
        signal = 0
        confidence = 0.0
        reasoning = f"Price Z-Score is {last_z:.2f} (Within normal distribution)."
        
        if prev_z < -self.z_threshold and last_z >= -self.z_threshold:
            signal = 1
            confidence = min(0.85, abs(prev_z) / 4.0)
            reasoning = f"Price was extremely undervalued (Z-Score was {prev_z:.2f}) and is reverting back to the mean."
        elif prev_z > self.z_threshold and last_z <= self.z_threshold:
            signal = -1
            confidence = min(0.85, abs(prev_z) / 4.0)
            reasoning = f"Price was extremely overvalued (Z-Score was {prev_z:.2f}) and is reverting back to the mean."
            
        entry_price = float(close.iloc[-1])
        stop_dist = 1.5 * float(atr.iloc[-1])
        
        return {
            "signal": signal,
            "confidence": round(confidence, 3),
            "entry_price": entry_price,
            "stop_loss": round(entry_price - stop_dist if signal == 1 else entry_price + stop_dist, 2),
            "take_profit": round(entry_price + 2 * stop_dist if signal == 1 else entry_price - 2 * stop_dist, 2),
            "reasoning": reasoning
        }

# === Category 4: Breakout ===

class DonchianBreakoutStrategy(BaseStrategy):
    def __init__(self, period: int = 20):
        super().__init__("Donchian Channel Breakout", "Breakout")
        self.period = period

    def generate_signal(self, df: pd.DataFrame, atr: pd.Series) -> Dict[str, Any]:
        if len(df) < self.period + 1:
            return {"signal": 0, "confidence": 0.0, "reasoning": "Insufficient data"}
            
        high = df['high']
        low = df['low']
        close = df['close']
        
        # Donchian channel limits are based on previous candles
        upper_ch = high.shift(1).rolling(window=self.period).max()
        lower_ch = low.shift(1).rolling(window=self.period).min()
        
        last_close = close.iloc[-1]
        prev_close = close.iloc[-2]
        
        signal = 0
        confidence = 0.0
        reasoning = f"Price is inside Donchian Channel range (${lower_ch.iloc[-1]:.2f} - ${upper_ch.iloc[-1]:.2f})."
        
        if last_close > upper_ch.iloc[-1] and prev_close <= upper_ch.iloc[-2]:
            signal = 1
            confidence = min(0.85, 0.5 + (last_close - upper_ch.iloc[-1]) / (atr.iloc[-1] + 1e-10))
            reasoning = f"Price broke out above the 20-period Donchian Channel resistance at ${upper_ch.iloc[-1]:.2f}."
        elif last_close < lower_ch.iloc[-1] and prev_close >= lower_ch.iloc[-2]:
            signal = -1
            confidence = min(0.85, 0.5 + (lower_ch.iloc[-1] - last_close) / (atr.iloc[-1] + 1e-10))
            reasoning = f"Price broke down below the 20-period Donchian Channel support at ${lower_ch.iloc[-1]:.2f}."
            
        entry_price = float(last_close)
        stop_dist = 1.5 * float(atr.iloc[-1])
        
        return {
            "signal": signal,
            "confidence": round(confidence, 3),
            "entry_price": entry_price,
            "stop_loss": round(entry_price - stop_dist if signal == 1 else entry_price + stop_dist, 2),
            "take_profit": round(entry_price + 2 * stop_dist if signal == 1 else entry_price - 2 * stop_dist, 2),
            "reasoning": reasoning
        }

class ATRBreakoutStrategy(BaseStrategy):
    def __init__(self, period: int = 20, num_atr: float = 2.0):
        super().__init__("ATR Breakout", "Breakout")
        self.period = period
        self.num_atr = num_atr

    def generate_signal(self, df: pd.DataFrame, atr: pd.Series) -> Dict[str, Any]:
        if len(df) < self.period:
            return {"signal": 0, "confidence": 0.0, "reasoning": "Insufficient data"}
            
        close = df['close']
        sma = get_sma(close, self.period)
        
        upper_ch = sma + self.num_atr * atr
        lower_ch = sma - self.num_atr * atr
        
        last_close = close.iloc[-1]
        prev_close = close.iloc[-2]
        
        signal = 0
        confidence = 0.0
        reasoning = "Volatility is normal, no ATR channel breakout."
        
        if last_close > upper_ch.iloc[-1] and prev_close <= upper_ch.iloc[-2]:
            signal = 1
            confidence = 0.75
            reasoning = f"Price broke above volatility-based ATR channel resistance at ${upper_ch.iloc[-1]:.2f}."
        elif last_close < lower_ch.iloc[-1] and prev_close >= lower_ch.iloc[-2]:
            signal = -1
            confidence = 0.75
            reasoning = f"Price broke below volatility-based ATR channel support at ${lower_ch.iloc[-1]:.2f}."
            
        entry_price = float(last_close)
        stop_dist = 1.5 * float(atr.iloc[-1])
        
        return {
            "signal": signal,
            "confidence": confidence,
            "entry_price": entry_price,
            "stop_loss": round(entry_price - stop_dist if signal == 1 else entry_price + stop_dist, 2),
            "take_profit": round(entry_price + 2 * stop_dist if signal == 1 else entry_price - 2 * stop_dist, 2),
            "reasoning": reasoning
        }

class RangeBreakoutStrategy(BaseStrategy):
    def __init__(self, range_period: int = 15, max_range_atr: float = 1.5):
        super().__init__("Range Breakout", "Breakout")
        self.range_period = range_period
        self.max_range_atr = max_range_atr

    def generate_signal(self, df: pd.DataFrame, atr: pd.Series) -> Dict[str, Any]:
        if len(df) < self.range_period + 1:
            return {"signal": 0, "confidence": 0.0, "reasoning": "Insufficient data"}
            
        high = df['high']
        low = df['low']
        close = df['close']
        
        # Calculate range dimensions of previous candles
        prev_highs = high.shift(1).rolling(window=self.range_period)
        prev_lows = low.shift(1).rolling(window=self.range_period)
        
        range_high = prev_highs.max()
        range_low = prev_lows.min()
        range_height = range_high - range_low
        
        last_close = close.iloc[-1]
        prev_close = close.iloc[-2]
        
        signal = 0
        confidence = 0.0
        reasoning = "Market is not consolidating or breakout has not occurred."
        
        # Check if the market was indeed in a tight range (consolidation)
        last_atr = atr.iloc[-1]
        is_consolidated = range_height.iloc[-1] <= self.max_range_atr * last_atr
        
        if is_consolidated:
            if last_close > range_high.iloc[-1] and prev_close <= range_high.iloc[-2]:
                signal = 1
                confidence = 0.8
                reasoning = f"Price broke out above a consolidation range of height ${range_height.iloc[-1]:.2f}."
            elif last_close < range_low.iloc[-1] and prev_close >= range_low.iloc[-2]:
                signal = -1
                confidence = 0.8
                reasoning = f"Price broke down below a consolidation range of height ${range_height.iloc[-1]:.2f}."
                
        entry_price = float(last_close)
        stop_dist = 1.5 * float(last_atr)
        
        return {
            "signal": signal,
            "confidence": confidence,
            "entry_price": entry_price,
            "stop_loss": round(entry_price - stop_dist if signal == 1 else entry_price + stop_dist, 2),
            "take_profit": round(entry_price + 2 * stop_dist if signal == 1 else entry_price - 2 * stop_dist, 2),
            "reasoning": reasoning
        }

# === Category 5: Volatility ===

class BollingerSqueezeStrategy(BaseStrategy):
    def __init__(self, period: int = 20, pct_threshold: float = 20.0):
        super().__init__("Bollinger Squeeze", "Volatility")
        self.period = period
        self.pct_threshold = pct_threshold

    def generate_signal(self, df: pd.DataFrame, atr: pd.Series) -> Dict[str, Any]:
        if len(df) < self.period + 10:
            return {"signal": 0, "confidence": 0.0, "reasoning": "Insufficient data"}
            
        close = df['close']
        sma = get_sma(close, self.period)
        std = close.rolling(window=self.period).std()
        
        upper_band = sma + 2 * std
        lower_band = sma - 2 * std
        bandwidth = (upper_band - lower_band) / (sma + 1e-10)
        
        # Calculate historical bandwidth percentile
        hist_bw = bandwidth.rolling(window=100)
        min_bw = hist_bw.min()
        max_bw = hist_bw.max()
        bw_pct = 100 * (bandwidth - min_bw) / (max_bw - min_bw + 1e-10)
        
        last_pct = bw_pct.iloc[-1]
        prev_pct = bw_pct.iloc[-2]
        
        signal = 0
        confidence = 0.0
        reasoning = f"Bandwidth is in the {last_pct:.1f} percentile (No squeeze/expansion trigger)."
        
        # Trigger when bandwidth expands out of a deep squeeze (< self.pct_threshold)
        if prev_pct < self.pct_threshold and last_pct >= self.pct_threshold:
            # Direction is determined by position relative to center line
            if close.iloc[-1] > sma.iloc[-1]:
                signal = 1
                confidence = 0.8
                reasoning = "Volatility squeeze is releasing to the upside."
            else:
                signal = -1
                confidence = 0.8
                reasoning = "Volatility squeeze is releasing to the downside."
                
        entry_price = float(close.iloc[-1])
        stop_dist = 2 * float(atr.iloc[-1])
        
        return {
            "signal": signal,
            "confidence": confidence,
            "entry_price": entry_price,
            "stop_loss": round(entry_price - stop_dist if signal == 1 else entry_price + stop_dist, 2),
            "take_profit": round(entry_price + 2 * stop_dist if signal == 1 else entry_price - 2 * stop_dist, 2),
            "reasoning": reasoning
        }

class KeltnerExpansionStrategy(BaseStrategy):
    def __init__(self, period: int = 20, multiplier: float = 2.0):
        super().__init__("Keltner Expansion", "Volatility")
        self.period = period
        self.multiplier = multiplier

    def generate_signal(self, df: pd.DataFrame, atr: pd.Series) -> Dict[str, Any]:
        if len(df) < self.period:
            return {"signal": 0, "confidence": 0.0, "reasoning": "Insufficient data"}
            
        close = df['close']
        ema = get_ema(close, self.period)
        
        upper_k = ema + self.multiplier * atr
        lower_k = ema - self.multiplier * atr
        
        last_close = close.iloc[-1]
        prev_close = close.iloc[-2]
        
        signal = 0
        confidence = 0.0
        reasoning = "Price stays within Keltner Channels."
        
        if last_close > upper_k.iloc[-1] and prev_close <= upper_k.iloc[-2]:
            signal = 1
            confidence = 0.72
            reasoning = "Volatility expansion: price broke above Keltner Channel resistance."
        elif last_close < lower_k.iloc[-1] and prev_close >= lower_k.iloc[-2]:
            signal = -1
            confidence = 0.72
            reasoning = "Volatility expansion: price broke below Keltner Channel support."
            
        entry_price = float(last_close)
        stop_dist = 1.5 * float(atr.iloc[-1])
        
        return {
            "signal": signal,
            "confidence": confidence,
            "entry_price": entry_price,
            "stop_loss": round(entry_price - stop_dist if signal == 1 else entry_price + stop_dist, 2),
            "take_profit": round(entry_price + 2 * stop_dist if signal == 1 else entry_price - 2 * stop_dist, 2),
            "reasoning": reasoning
        }

class ATRExpansionStrategy(BaseStrategy):
    def __init__(self, period: int = 14, filter_period: int = 20):
        super().__init__("ATR Expansion", "Volatility")
        self.period = period
        self.filter_period = filter_period

    def generate_signal(self, df: pd.DataFrame, atr: pd.Series) -> Dict[str, Any]:
        if len(df) < self.filter_period + 10:
            return {"signal": 0, "confidence": 0.0, "reasoning": "Insufficient data"}
            
        close = df['close']
        ema_atr = get_ema(atr, self.filter_period)
        
        last_atr = atr.iloc[-1]
        last_ema_atr = ema_atr.iloc[-1]
        
        signal = 0
        confidence = 0.0
        reasoning = f"ATR is {last_atr:.4f} below its EMA of {last_ema_atr:.4f} (No volatility expansion)."
        
        # Volatility is expanding (ATR exceeds its long term average)
        if last_atr > 1.3 * last_ema_atr:
            # Check price direction to align signal
            ema_trend_fast = get_ema(close, 9)
            ema_trend_slow = get_ema(close, 21)
            
            if ema_trend_fast.iloc[-1] > ema_trend_slow.iloc[-1]:
                signal = 1
                confidence = min(0.85, last_atr / (last_ema_atr + 1e-10) - 0.5)
                reasoning = "Volatility (ATR) is expanding rapidly while trend is bullish."
            elif ema_trend_fast.iloc[-1] < ema_trend_slow.iloc[-1]:
                signal = -1
                confidence = min(0.85, last_atr / (last_ema_atr + 1e-10) - 0.5)
                reasoning = "Volatility (ATR) is expanding rapidly while trend is bearish."
                
        entry_price = float(close.iloc[-1])
        stop_dist = 2 * float(atr.iloc[-1])
        
        return {
            "signal": signal,
            "confidence": round(confidence, 3),
            "entry_price": entry_price,
            "stop_loss": round(entry_price - stop_dist if signal == 1 else entry_price + stop_dist, 2),
            "take_profit": round(entry_price + 2 * stop_dist if signal == 1 else entry_price - 2 * stop_dist, 2),
            "reasoning": reasoning
        }

# === Category 6: Volume-Based ===

class OBVVolumeStrategy(BaseStrategy):
    def __init__(self, period: int = 20):
        super().__init__("OBV", "Volume-Based")
        self.period = period

    def generate_signal(self, df: pd.DataFrame, atr: pd.Series) -> Dict[str, Any]:
        if len(df) < self.period + 1:
            return {"signal": 0, "confidence": 0.0, "reasoning": "Insufficient data"}
            
        close = df['close']
        volume = df['volume']
        
        obv = np.zeros(len(df))
        obv[0] = volume.iloc[0]
        
        for i in range(1, len(df)):
            if close.iloc[i] > close.iloc[i-1]:
                obv[i] = obv[i-1] + volume.iloc[i]
            elif close.iloc[i] < close.iloc[i-1]:
                obv[i] = obv[i-1] - volume.iloc[i]
            else:
                obv[i] = obv[i-1]
                
        obv_series = pd.Series(obv, index=df.index)
        obv_max = obv_series.shift(1).rolling(window=self.period).max()
        obv_min = obv_series.shift(1).rolling(window=self.period).min()
        
        last_obv = obv_series.iloc[-1]
        
        signal = 0
        confidence = 0.0
        reasoning = "OBV volume is in a neutral accumulation range."
        
        # Bullish volume breakout
        if last_obv > obv_max.iloc[-1] and close.iloc[-1] > get_sma(close, self.period).iloc[-1]:
            signal = 1
            confidence = 0.7
            reasoning = "OBV broke out to a 20-period high, indicating strong volume-backed accumulation."
        # Bearish volume breakdown
        elif last_obv < obv_min.iloc[-1] and close.iloc[-1] < get_sma(close, self.period).iloc[-1]:
            signal = -1
            confidence = 0.7
            reasoning = "OBV broke down to a 20-period low, indicating strong volume-backed distribution."
            
        entry_price = float(close.iloc[-1])
        stop_dist = 2 * float(atr.iloc[-1])
        
        return {
            "signal": signal,
            "confidence": confidence,
            "entry_price": entry_price,
            "stop_loss": round(entry_price - stop_dist if signal == 1 else entry_price + stop_dist, 2),
            "take_profit": round(entry_price + 2 * stop_dist if signal == 1 else entry_price - 2 * stop_dist, 2),
            "reasoning": reasoning
        }

class VWAPCrossStrategy(BaseStrategy):
    def __init__(self, vwap_window: int = 24):
        super().__init__("VWAP", "Volume-Based")
        self.vwap_window = vwap_window

    def generate_signal(self, df: pd.DataFrame, atr: pd.Series) -> Dict[str, Any]:
        if len(df) < self.vwap_window:
            return {"signal": 0, "confidence": 0.0, "reasoning": "Insufficient data"}
            
        close = df['close']
        volume = df['volume']
        typical_price = (df['high'] + df['low'] + close) / 3
        
        tp_v = typical_price * volume
        cum_tp_v = tp_v.rolling(window=self.vwap_window).sum()
        cum_vol = volume.rolling(window=self.vwap_window).sum()
        
        vwap = cum_tp_v / (cum_vol + 1e-10)
        
        last_close = close.iloc[-1]
        prev_close = close.iloc[-2]
        last_vwap = vwap.iloc[-1]
        prev_vwap = vwap.iloc[-2]
        
        signal = 0
        confidence = 0.0
        reasoning = f"Price is tracking close to VWAP at ${last_vwap:.2f}."
        
        if prev_close <= prev_vwap and last_close > last_vwap:
            signal = 1
            confidence = 0.75
            reasoning = f"Price crossed above VWAP (${last_vwap:.2f}), confirming bullish volume strength."
        elif prev_close >= prev_vwap and last_close < last_vwap:
            signal = -1
            confidence = 0.75
            reasoning = f"Price crossed below VWAP (${last_vwap:.2f}), confirming bearish volume weakness."
            
        entry_price = float(last_close)
        stop_dist = 2 * float(atr.iloc[-1])
        
        return {
            "signal": signal,
            "confidence": confidence,
            "entry_price": entry_price,
            "stop_loss": round(entry_price - stop_dist if signal == 1 else entry_price + stop_dist, 2),
            "take_profit": round(entry_price + 2 * stop_dist if signal == 1 else entry_price - 2 * stop_dist, 2),
            "reasoning": reasoning
        }

class VolumeSpikeStrategy(BaseStrategy):
    def __init__(self, sma_period: int = 20, volume_multiplier: float = 2.5):
        super().__init__("Volume Spike Detection", "Volume-Based")
        self.sma_period = sma_period
        self.volume_multiplier = volume_multiplier

    def generate_signal(self, df: pd.DataFrame, atr: pd.Series) -> Dict[str, Any]:
        if len(df) < self.sma_period:
            return {"signal": 0, "confidence": 0.0, "reasoning": "Insufficient data"}
            
        close = df['close']
        volume = df['volume']
        
        vol_sma = get_sma(volume, self.sma_period)
        
        last_vol = volume.iloc[-1]
        last_sma = vol_sma.iloc[-1]
        
        signal = 0
        confidence = 0.0
        reasoning = f"Volume is normal (${last_vol:.1f} quote units)."
        
        if last_vol > self.volume_multiplier * last_sma:
            # Volume spike detected! Determine price direction
            is_bullish = close.iloc[-1] > df['open'].iloc[-1]
            if is_bullish:
                signal = 1
                confidence = min(0.9, last_vol / (last_sma + 1e-10) / 5.0)
                reasoning = f"Institutional Volume Spike: volume is {last_vol/last_sma:.1f}x higher than average on a bullish candle."
            else:
                signal = -1
                confidence = min(0.9, last_vol / (last_sma + 1e-10) / 5.0)
                reasoning = f"Institutional Volume Spike: volume is {last_vol/last_sma:.1f}x higher than average on a bearish candle."
                
        entry_price = float(close.iloc[-1])
        stop_dist = 2 * float(atr.iloc[-1])
        
        return {
            "signal": signal,
            "confidence": round(confidence, 3),
            "entry_price": entry_price,
            "stop_loss": round(entry_price - stop_dist if signal == 1 else entry_price + stop_dist, 2),
            "take_profit": round(entry_price + 2 * stop_dist if signal == 1 else entry_price - 2 * stop_dist, 2),
            "reasoning": reasoning
        }

# === Category 7: Smart Money Concepts (SMC) ===

class OrderBlockStrategy(BaseStrategy):
    def __init__(self, lookback: int = 50):
        super().__init__("Order Blocks", "Smart Money Concepts")
        self.lookback = lookback

    def generate_signal(self, df: pd.DataFrame, atr: pd.Series) -> Dict[str, Any]:
        if len(df) < self.lookback:
            return {"signal": 0, "confidence": 0.0, "reasoning": "Insufficient data"}
            
        close = df['close']
        high = df['high']
        low = df['low']
        open_p = df['open']
        volume = df['volume']
        
        # Detect swing points
        # 1. Identify bullish expansions: high volume positive candle breaking a local structure
        # Bullish Order Block = the last bearish candle before this expansion.
        # Find order blocks within lookback
        entry_price = float(close.iloc[-1])
        signal = 0
        confidence = 0.0
        reasoning = "No active order blocks mitigated."
        stop_loss = 0.0
        take_profit = 0.0
        
        vol_sma = get_sma(volume, 20).iloc[-1]
        
        # Scan backward from recent history to find the most recent order blocks
        for idx in range(len(df) - 5, len(df) - 25, -1):
            if idx < 2:
                continue
            
            # Condition for Bullish Expansion at idx+1
            is_expansion = (close.iloc[idx+1] > open_p.iloc[idx+1]) and (volume.iloc[idx+1] > 1.8 * vol_sma)
            if is_expansion:
                # The bearish candle at idx is the Order Block candidate
                if close.iloc[idx] < open_p.iloc[idx]:
                    ob_high = float(high.iloc[idx])
                    ob_low = float(low.iloc[idx])
                    
                    # Check if the current close has retraced into this order block
                    if entry_price > ob_low and entry_price <= ob_high:
                        signal = 1
                        confidence = 0.82
                        reasoning = f"Price retraced into a Bullish Order Block (High: ${ob_high:.2f}, Low: ${ob_low:.2f}) created N={len(df)-1-idx} bars ago."
                        stop_loss = round(ob_low - 0.5 * float(atr.iloc[-1]), 2)
                        take_profit = round(entry_price + (entry_price - stop_loss) * 2.0, 2)
                        break
                        
            # Condition for Bearish Expansion at idx+1
            is_bearish_expansion = (close.iloc[idx+1] < open_p.iloc[idx+1]) and (volume.iloc[idx+1] > 1.8 * vol_sma)
            if is_bearish_expansion:
                # The bullish candle at idx is the Bearish OB
                if close.iloc[idx] > open_p.iloc[idx]:
                    ob_high = float(high.iloc[idx])
                    ob_low = float(low.iloc[idx])
                    
                    # Check if price has retraced into the bearish OB
                    if entry_price >= ob_low and entry_price < ob_high:
                        signal = -1
                        confidence = 0.82
                        reasoning = f"Price retraced into a Bearish Order Block (High: ${ob_high:.2f}, Low: ${ob_low:.2f}) created N={len(df)-1-idx} bars ago."
                        stop_loss = round(ob_high + 0.5 * float(atr.iloc[-1]), 2)
                        take_profit = round(entry_price - (stop_loss - entry_price) * 2.0, 2)
                        break
                        
        if signal == 0:
            return {"signal": 0, "confidence": 0.0, "reasoning": reasoning}
            
        return {
            "signal": signal,
            "confidence": confidence,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "reasoning": reasoning
        }

class FairValueGapStrategy(BaseStrategy):
    def __init__(self, lookback: int = 30):
        super().__init__("Fair Value Gaps", "Smart Money Concepts")
        self.lookback = lookback

    def generate_signal(self, df: pd.DataFrame, atr: pd.Series) -> Dict[str, Any]:
        if len(df) < self.lookback:
            return {"signal": 0, "confidence": 0.0, "reasoning": "Insufficient data"}
            
        high = df['high']
        low = df['low']
        close = df['close']
        
        signal = 0
        confidence = 0.0
        reasoning = "No unmitigated Fair Value Gaps detected."
        
        # A Bullish FVG occurs when low of candle N is greater than high of candle N-2
        # A Bearish FVG occurs when high of candle N is less than low of candle N-2
        entry_price = float(close.iloc[-1])
        stop_loss = 0.0
        take_profit = 0.0
        
        # Scan backward
        for idx in range(len(df) - 1, len(df) - 15, -1):
            if idx < 2:
                continue
            
            # Check Bullish FVG
            fvg_low = low.iloc[idx]
            fvg_high = high.iloc[idx-2]
            
            if fvg_low > fvg_high:
                # FVG exists between index idx-2 and idx. It is unmitigated if the current price is within this range.
                if entry_price > fvg_high and entry_price < fvg_low:
                    signal = 1
                    confidence = 0.8
                    reasoning = f"Price is filling a Bullish Fair Value Gap (FVG) between ${fvg_high:.2f} and ${fvg_low:.2f}."
                    stop_loss = round(fvg_high - 0.5 * float(atr.iloc[-1]), 2)
                    take_profit = round(entry_price + (entry_price - stop_loss) * 2.0, 2)
                    break
                    
            # Check Bearish FVG
            fvg_high = high.iloc[idx]
            fvg_low = low.iloc[idx-2]
            
            if fvg_high < fvg_low:
                if entry_price > fvg_high and entry_price < fvg_low:
                    signal = -1
                    confidence = 0.8
                    reasoning = f"Price is filling a Bearish Fair Value Gap (FVG) between ${fvg_high:.2f} and ${fvg_low:.2f}."
                    stop_loss = round(fvg_low + 0.5 * float(atr.iloc[-1]), 2)
                    take_profit = round(entry_price - (stop_loss - entry_price) * 2.0, 2)
                    break
                    
        if signal == 0:
            return {"signal": 0, "confidence": 0.0, "reasoning": reasoning}
            
        return {
            "signal": signal,
            "confidence": confidence,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "reasoning": reasoning
        }

class BOS_CHOCH_Strategy(BaseStrategy):
    def __init__(self, period: int = 15):
        super().__init__("BOS & CHOCH", "Smart Money Concepts")
        self.period = period

    def generate_signal(self, df: pd.DataFrame, atr: pd.Series) -> Dict[str, Any]:
        if len(df) < self.period * 2:
            return {"signal": 0, "confidence": 0.0, "reasoning": "Insufficient data"}
            
        close = df['close']
        high = df['high']
        low = df['low']
        
        # Calculate local swing highs and swing lows (fractals)
        # Swing High = High[i] is higher than previous and next 2 highs
        # Swing Low = Low[i] is lower than previous and next 2 lows
        # Let's find recent swing points
        swing_highs = []
        swing_lows = []
        
        for i in range(2, len(df) - 2):
            if high.iloc[i] > high.iloc[i-1] and high.iloc[i] > high.iloc[i-2] and \
               high.iloc[i] > high.iloc[i+1] and high.iloc[i] > high.iloc[i+2]:
                swing_highs.append((i, high.iloc[i]))
            if low.iloc[i] < low.iloc[i-1] and low.iloc[i] < low.iloc[i-2] and \
               low.iloc[i] < low.iloc[i+1] and low.iloc[i] < low.iloc[i+2]:
                swing_lows.append((i, low.iloc[i]))
                
        signal = 0
        confidence = 0.0
        reasoning = "Market structure remains intact, no Break of Structure (BOS)."
        
        # Check if latest candle closed above/below the most recent swing high/low
        if swing_highs and swing_lows:
            last_swing_high = swing_highs[-1][1]
            last_swing_low = swing_lows[-1][1]
            
            last_close = close.iloc[-1]
            prev_close = close.iloc[-2]
            
            # Bullish Break of Structure (BOS)
            if prev_close <= last_swing_high and last_close > last_swing_high:
                signal = 1
                confidence = 0.8
                reasoning = f"Bullish Break of Structure (BOS): Price broke local market structure above swing high of ${last_swing_high:.2f}."
            # Bearish Break of Structure (BOS)
            elif prev_close >= last_swing_low and last_close < last_swing_low:
                signal = -1
                confidence = 0.8
                reasoning = f"Bearish Break of Structure (BOS): Price broke local market structure below swing low of ${last_swing_low:.2f}."
                
        entry_price = float(close.iloc[-1])
        stop_dist = 2 * float(atr.iloc[-1])
        
        return {
            "signal": signal,
            "confidence": confidence,
            "entry_price": entry_price,
            "stop_loss": round(entry_price - stop_dist if signal == 1 else entry_price + stop_dist, 2),
            "take_profit": round(entry_price + 2 * stop_dist if signal == 1 else entry_price - 2 * stop_dist, 2),
            "reasoning": reasoning
        }

class LiquiditySweepStrategy(BaseStrategy):
    def __init__(self, period: int = 30):
        super().__init__("Liquidity Sweeps", "Smart Money Concepts")
        self.period = period

    def generate_signal(self, df: pd.DataFrame, atr: pd.Series) -> Dict[str, Any]:
        if len(df) < self.period:
            return {"signal": 0, "confidence": 0.0, "reasoning": "Insufficient data"}
            
        close = df['close']
        high = df['high']
        low = df['low']
        
        # Find swing high and swing low in the previous candles (excluding the current candle)
        prev_highs = high.iloc[:-1]
        prev_lows = low.iloc[:-1]
        
        key_high = prev_highs.rolling(window=self.period).max().iloc[-1]
        key_low = prev_lows.rolling(window=self.period).min().iloc[-1]
        
        last_high = high.iloc[-1]
        last_low = low.iloc[-1]
        last_close = close.iloc[-1]
        
        signal = 0
        confidence = 0.0
        reasoning = "No liquidity sweeps detected at boundaries."
        
        # Bullish Sweep: Price spikes below key low, but closes back above it
        if last_low < key_low and last_close > key_low:
            signal = 1
            confidence = 0.85
            reasoning = f"Bullish Liquidity Sweep: Price swept sell-side liquidity below swing low of ${key_low:.2f} and closed back inside."
        # Bearish Sweep: Price spikes above key high, but closes back below it
        elif last_high > key_high and last_close < key_high:
            signal = -1
            confidence = 0.85
            reasoning = f"Bearish Liquidity Sweep: Price swept buy-side liquidity above swing high of ${key_high:.2f} and closed back inside."
            
        entry_price = float(last_close)
        stop_dist = 1.5 * float(atr.iloc[-1])
        
        return {
            "signal": signal,
            "confidence": confidence,
            "entry_price": entry_price,
            "stop_loss": round(entry_price - stop_dist if signal == 1 else entry_price + stop_dist, 2),
            "take_profit": round(entry_price + 2 * stop_dist if signal == 1 else entry_price - 2 * stop_dist, 2),
            "reasoning": reasoning
        }

# === Market Regime Detector ===

class MarketRegimeDetector:
    @staticmethod
    def detect_regime(df: pd.DataFrame, atr: pd.Series) -> Tuple[str, Dict[str, Any]]:
        """
        Detect current market regime.
        Regimes:
          - TREND_BULLISH
          - TREND_BEARISH
          - RANGING
          - HIGH_VOLATILITY
          - SMC_ACCUMULATION
          - SMC_DISTRIBUTION
        """
        close = df['close']
        volume = df['volume']
        
        # Calculate indicators
        ema_fast = get_ema(close, 20)
        ema_slow = get_ema(close, 50)
        
        # ADX (simplified version for speed)
        up_move = df['high'].diff()
        down_move = -df['low'].diff()
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
        tr = pd.concat([df['high'] - df['low'], (df['high'] - close.shift(1)).abs(), (df['low'] - close.shift(1)).abs()], axis=1).max(axis=1)
        atr_sum = tr.rolling(window=14, min_periods=1).sum()
        plus_di = 100 * pd.Series(plus_dm).rolling(window=14, min_periods=1).sum() / (atr_sum + 1e-10)
        minus_di = 100 * pd.Series(minus_dm).rolling(window=14, min_periods=1).sum() / (atr_sum + 1e-10)
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-10)
        adx = dx.rolling(window=14, min_periods=1).mean().iloc[-1]
        
        # Bollinger Bandwidth
        sma = get_sma(close, 20)
        std = close.rolling(window=20, min_periods=1).std()
        bandwidth = ((sma + 2*std) - (sma - 2*std)) / (sma + 1e-10)
        last_bw = bandwidth.iloc[-1]
        mean_bw = bandwidth.rolling(window=100, min_periods=1).mean().iloc[-1]
        
        # ATR / Volatility
        last_atr = atr.iloc[-1]
        mean_atr = atr.rolling(window=100, min_periods=1).mean().iloc[-1]
        
        # OBV for accumulation / distribution
        obv = np.zeros(len(df))
        obv[0] = volume.iloc[0]
        for i in range(1, len(df)):
            if close.iloc[i] > close.iloc[i-1]:
                obv[i] = obv[i-1] + volume.iloc[i]
            elif close.iloc[i] < close.iloc[i-1]:
                obv[i] = obv[i-1] - volume.iloc[i]
            else:
                obv[i] = obv[i-1]
        obv_series = pd.Series(obv, index=df.index)
        obv_trend = obv_series.diff().rolling(window=20, min_periods=1).mean().iloc[-1]
        
        # Rules logic
        metrics = {
            "adx": round(adx, 2),
            "bandwidth": round(last_bw, 4),
            "mean_bandwidth": round(mean_bw, 4),
            "atr": round(last_atr, 4),
            "mean_atr": round(mean_atr, 4),
            "obv_trend": round(obv_trend, 2)
        }
        
        # 1. High Volatility
        if last_atr > 1.5 * mean_atr:
            return "HIGH_VOLATILITY", metrics
            
        # 2. Trending
        if adx > 25:
            if ema_fast.iloc[-1] > ema_slow.iloc[-1]:
                return "TREND_BULLISH", metrics
            else:
                return "TREND_BEARISH", metrics
                
        # 3. SMC Accumulation / Distribution (tight range with buying/selling pressure)
        if last_bw < 0.8 * mean_bw:
            if obv_trend > 0:
                return "SMC_ACCUMULATION", metrics
            else:
                return "SMC_DISTRIBUTION", metrics
                
        # 4. Ranging (Default flat market)
        return "RANGING", metrics

# === Strategy Selector ===

class StrategySelector:
    def __init__(self, state_file_path: str = "strategy_performance.json"):
        self.state_file_path = state_file_path
        self.strategies: List[BaseStrategy] = [
            # Trend Following
            EMACrossStrategy(),
            SMACrossStrategy(),
            SupertrendStrategy(),
            ADXTrendStrategy(),
            # Momentum
            MACDMomentumStrategy(),
            RSIMomentumStrategy(),
            StochasticMomentumStrategy(),
            ROCMomentumStrategy(),
            # Mean Reversion
            BollingerBandsReversionStrategy(),
            RSIReversionStrategy(),
            ZScoreReversionStrategy(),
            # Breakout
            DonchianBreakoutStrategy(),
            ATRBreakoutStrategy(),
            RangeBreakoutStrategy(),
            # Volatility
            BollingerSqueezeStrategy(),
            KeltnerExpansionStrategy(),
            ATRExpansionStrategy(),
            # Volume-Based
            OBVVolumeStrategy(),
            VWAPCrossStrategy(),
            VolumeSpikeStrategy(),
            # SMC
            OrderBlockStrategy(),
            FairValueGapStrategy(),
            BOS_CHOCH_Strategy(),
            LiquiditySweepStrategy()
        ]
        
        # Load historical performance
        self.performance = self._load_performance()

        # Define weight matrix for each regime
        self.regime_weights = {
            "TREND_BULLISH": {
                "Trend Following": 1.5, "Momentum": 1.2, "Mean Reversion": 0.5,
                "Breakout": 1.0, "Volatility": 1.0, "Volume-Based": 1.1, "Smart Money Concepts": 1.3
            },
            "TREND_BEARISH": {
                "Trend Following": 1.5, "Momentum": 1.2, "Mean Reversion": 0.5,
                "Breakout": 1.0, "Volatility": 1.0, "Volume-Based": 1.1, "Smart Money Concepts": 1.3
            },
            "RANGING": {
                "Mean Reversion": 1.6, "Trend Following": 0.4, "Momentum": 0.7,
                "Breakout": 0.5, "Volatility": 0.6, "Volume-Based": 0.9, "Smart Money Concepts": 1.2
            },
            "HIGH_VOLATILITY": {
                "Breakout": 1.6, "Volatility": 1.4, "Mean Reversion": 0.8,
                "Trend Following": 1.0, "Momentum": 1.1, "Volume-Based": 1.2, "Smart Money Concepts": 1.0
            },
            "SMC_ACCUMULATION": {
                "Smart Money Concepts": 1.7, "Volume-Based": 1.4, "Breakout": 1.2,
                "Mean Reversion": 1.1, "Volatility": 1.1, "Momentum": 0.9, "Trend Following": 0.8
            },
            "SMC_DISTRIBUTION": {
                "Smart Money Concepts": 1.7, "Volume-Based": 1.4, "Breakout": 1.2,
                "Mean Reversion": 1.1, "Volatility": 1.1, "Momentum": 0.9, "Trend Following": 0.8
            }
        }

    def _load_performance(self) -> Dict[str, Any]:
        if os.path.exists(self.state_file_path):
            try:
                with open(self.state_file_path) as f:
                    return json.load(f)
            except:
                pass
        
        # Initialize default performance state
        default_perf = {}
        for s in self.strategies:
            default_perf[s.name] = {
                "wins": 0,
                "losses": 0,
                "pnl": 0.0,
                "total_trades": 0
            }
        return default_perf

    def save_performance(self):
        with open(self.state_file_path, "w") as f:
            json.dump(self.performance, f, indent=2)

    def record_trade_result(self, strategy_name: str, pnl: float):
        if strategy_name in self.performance:
            perf = self.performance[strategy_name]
            perf["total_trades"] += 1
            perf["pnl"] += pnl
            if pnl > 0:
                perf["wins"] += 1
            else:
                perf["losses"] += 1
            self.save_performance()

    def select_best_trade(self, df: pd.DataFrame, style: Optional[str] = None) -> Dict[str, Any]:
        """
        Run all strategies, detect regime, rank them, and return the winning setup.
        """
        if len(df) < 55:
            return {
                "symbol": "UNKNOWN",
                "decision": "HOLD",
                "confidence": "LOW",
                "strategy": "None",
                "score": 0.0,
                "reasoning": "Insufficient historical candles for multi-strategy evaluation."
            }
            
        # 1. Compute ATR once for all strategies
        atr = get_atr(df, 14)
        
        # 2. Detect regime
        regime, regime_metrics = MarketRegimeDetector.detect_regime(df, atr)
        
        # 3. Collect strategy signals
        raw_signals = []
        for strat in self.strategies:
            try:
                res = strat.generate_signal(df, atr)
                if res["signal"] != 0:
                    raw_signals.append({
                        "strategy": strat.name,
                        "category": strat.category,
                        "signal": res["signal"],
                        "confidence": res["confidence"],
                        "entry_price": res["entry_price"],
                        "stop_loss": res["stop_loss"],
                        "take_profit": res["take_profit"],
                        "reasoning": res["reasoning"]
                    })
            except Exception as e:
                # Fail-safe for individual strategy exceptions
                pass

        if not raw_signals:
            return {
                "decision": "HOLD",
                "confidence": "LOW",
                "strategy": "None",
                "score": 0.0,
                "reasoning": f"No strategies generated a trading signal. Market regime detected: {regime}."
            }

        # 4. Score and Rank strategies using weight matrix
        ranked_signals = []
        for r_sig in raw_signals:
            category = r_sig["category"]
            strat_name = r_sig["strategy"]
            
            # Base confidence
            base_conf = r_sig["confidence"]
            
            # Regime multiplier
            multiplier = self.regime_weights.get(regime, {}).get(category, 1.0)
            
            # Adjust based on historical strategy win rate
            perf = self.performance.get(strat_name, {"wins": 0, "total_trades": 0})
            win_rate = (perf["wins"] / perf["total_trades"]) if perf["total_trades"] > 0 else 0.5
            perf_factor = 1.0 + (win_rate - 0.5) * 0.4  # scales from 0.8 (win rate 0) to 1.2 (win rate 1)
            
            adjusted_score = base_conf * multiplier * perf_factor
            
            r_sig["score"] = round(adjusted_score, 3)
            r_sig["regime_multiplier"] = multiplier
            r_sig["perf_factor"] = round(perf_factor, 3)
            ranked_signals.append(r_sig)

        # Sort by adjusted score descending
        ranked_signals.sort(key=lambda x: x["score"], reverse=True)
        winner = ranked_signals[0]
        
        # Adjust stop loss and take profit based on style
        entry_price = winner["entry_price"]
        sl = winner["stop_loss"]
        tp = winner["take_profit"]
        
        # 5. Formulate comparative reasoning
        decision_label = "BUY" if winner["signal"] == 1 else "SELL"
        confidence_label = "HIGH" if winner["score"] >= 0.85 else ("MEDIUM" if winner["score"] >= 0.5 else "LOW")
        
        reasoning_comp = (
            f"Strategy '{winner['strategy']}' selected with adjusted score {winner['score']:.2f}. "
            f"Current market regime is {regime} (ADX={regime_metrics['adx']}, Bandwidth={regime_metrics['bandwidth']}), which favors category '{winner['category']}' (multiplier: {winner['regime_multiplier']}x). "
            f"Winning setup: {winner['reasoning']}. "
        )
        
        if style == "scalping":
            # Tighter risk bounds: reduce default target/stop distance by half
            winner["stop_loss"] = round(entry_price - (entry_price - sl) * 0.5 if winner["signal"] == 1 else entry_price + (sl - entry_price) * 0.5, 4)
            winner["take_profit"] = round(entry_price + (tp - entry_price) * 0.5 if winner["signal"] == 1 else entry_price - (entry_price - tp) * 0.5, 4)
            reasoning_comp += " [Style: Scalping - Tighter volatility stops applied]"
        elif style == "swing":
            # Wider risk bounds to allow for swing flexibility
            winner["stop_loss"] = round(entry_price - (entry_price - sl) * 1.5 if winner["signal"] == 1 else entry_price + (sl - entry_price) * 1.5, 4)
            winner["take_profit"] = round(entry_price + (tp - entry_price) * 1.5 if winner["signal"] == 1 else entry_price - (entry_price - tp) * 1.5, 4)
            reasoning_comp += " [Style: Swing Trading - Expanded range stops applied]"
        
        if len(ranked_signals) > 1:
            alternatives = []
            for alt in ranked_signals[1:4]:
                alt_dir = "BUY" if alt["signal"] == 1 else "SELL"
                alternatives.append(f"{alt['strategy']} ({alt_dir} score={alt['score']:.2f})")
            reasoning_comp += f"Chosen over competing strategies: {', '.join(alternatives)}."
        else:
            reasoning_comp += "No competing strategies triggered signals."

        return {
            "decision": "STRONG BUY" if decision_label == "BUY" and confidence_label == "HIGH" else (
                        "STRONG SELL" if decision_label == "SELL" and confidence_label == "HIGH" else decision_label
            ),
            "confidence": confidence_label,
            "strategy": winner["strategy"],
            "score": winner["score"],
            "entry_price": winner["entry_price"],
            "stop_loss": winner["stop_loss"],
            "take_profit": winner["take_profit"],
            "reasoning": reasoning_comp,
            "regime": regime,
            "regime_metrics": regime_metrics,
            "ranked_opportunities": ranked_signals
        }

# === Self-Test / Demo Run ===
if __name__ == "__main__":
    print("[*] Instantiating Strategy Intelligence Layer...")
    selector = StrategySelector()
    print(f"[OK] Successfully initialized {len(selector.strategies)} strategies.")
    
    # Generate some dummy data to test calculations
    print("[*] Generating test OHLCV data...")
    dates = pd.date_range(start="2026-06-01", periods=100, freq="h")
    np.random.seed(42)
    close_prices = 100.0 + np.cumsum(np.random.normal(0, 1, 100))
    df = pd.DataFrame({
        "open": close_prices - np.random.uniform(0, 1, 100),
        "high": close_prices + np.random.uniform(0, 2, 100),
        "low": close_prices - np.random.uniform(0, 2, 100),
        "close": close_prices,
        "volume": np.random.uniform(1000, 5000, 100)
    }, index=dates)
    
    print("[*] Running strategy selection...")
    best_trade = selector.select_best_trade(df)
    print("\n=== SELECTED OPPORTUNITY ===")
    print(json.dumps(best_trade, indent=2))
