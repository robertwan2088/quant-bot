"""
动量突破策略
基于ATR和成交量突破
"""

from typing import Dict, List
import pandas as pd
import numpy as np


class MomentumStrategy:
    """动量突破策略"""
    
    def __init__(self, exchange, params: dict):
        self.exchange = exchange
        self.params = params
        
        # 策略参数
        self.atr_period = params.get("atr_period", 14)
        self.atr_multiplier = params.get("atr_multiplier", 2)
        self.volume_ma_period = params.get("volume_ma_period", 20)
        self.volume_threshold = params.get("volume_threshold", 1.5)
        
        # 状态
        self.breakout_high = 0
        self.breakout_low = 0
        
    def calculate_indicators(self, klines: List[Dict]) -> Dict:
        """计算技术指标"""
        if not klines or len(klines) < self.volume_ma_period + 10:
            return {}
        
        # 转换为DataFrame
        df = pd.DataFrame(klines)
        df['close'] = df['close'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['volume'] = df['volume'].astype(float)
        
        # 计算ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(window=self.atr_period).mean()
        
        # 计算成交量均线
        df['volume_ma'] = df['volume'].rolling(window=self.volume_ma_period).mean()
        
        # 计算价格动量
        df['momentum'] = df['close'].pct_change(periods=10)
        
        # 计算波动率
        df['volatility'] = df['close'].rolling(window=20).std() / df['close'].rolling(window=20).mean()
        
        return df
    
    async def analyze(self, symbol: str, market: Dict) -> Dict:
        """分析市场并生成信号"""
        klines = market.get("klines", [])
        
        if not klines or len(klines) < self.volume_ma_period + 10:
            return {"action": "hold", "reason": "数据不足"}
        
        df = self.calculate_indicators(klines)
        
        # 获取最新数据
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        current_price = last['close']
        atr = last['atr']
        volume_ma = last['volume_ma']
        volume = last['volume']
        momentum = last['momentum']
        
        # 计算突破位置
        if self.breakout_high == 0:
            # 初始化20日高点
            self.breakout_high = df['high'].iloc[-20:-1].max()
            self.breakout_low = df['low'].iloc[-20:-1].min()
        
        # 初始化结果
        result = {
            "action": "hold",
            "reason": "无突破信号",
            "indicators": {}
        }
        
        # 成交量突破
        volume_ratio = volume / volume_ma if volume_ma > 0 else 1
        volume_breakout = volume_ratio > self.volume_threshold
        
        # 价格突破
        price_breakout_up = current_price > self.breakout_high
        price_breakout_down = current_price < self.breakout_low
        
        # ATR止损位
        atr_stop_long = current_price - atr * self.atr_multiplier
        atr_stop_short = current_price + atr * self.atr_multiplier
        
        # 动量方向
        momentum_positive = momentum > 0
        
        # 记录指标
        result["indicators"] = {
            "price": current_price,
            "atr": atr,
            "volume_ratio": volume_ratio,
            "volume_breakout": volume_breakout,
            "price_breakout_up": price_breakout_up,
            "price_breakout_down": price_breakout_down,
            "momentum": momentum,
            "momentum_positive": momentum_positive,
            "breakout_high": self.breakout_high,
            "breakout_low": self.breakout_low,
            "atr_stop_long": atr_stop_long,
            "atr_stop_short": atr_stop_short
        }
        
        # 突破买入信号
        if price_breakout_up and volume_breakout and momentum_positive:
            result["action"] = "buy"
            result["reason"] = f"动量突破: 价格突破20日高点 + 成交量放大({volume_ratio:.1f}倍)"
            result["confidence"] = min(0.5 + volume_ratio / 5, 1.0)
            
            # 更新突破位
            self.breakout_high = current_price
            
        # 突破卖出信号
        elif price_breakout_down and volume_breakout and not momentum_positive:
            result["action"] = "sell"
            result["reason"] = f"动量跌破: 价格跌破20日低点 + 成交量放大({volume_ratio:.1f}倍)"
            result["confidence"] = min(0.5 + volume_ratio / 5, 1.0)
            
            # 更新突破位
            self.breakout_low = current_price
        
        # 更新突破位（持续上涨/下跌时）
        if current_price > self.breakout_high * 1.02:  # 2%更新
            self.breakout_high = df['high'].iloc[-10:].max()
        
        if current_price < self.breakout_low * 0.98:
            self.breakout_low = df['low'].iloc[-10:].min()
        
        return result
    
    def reset_breakout(self):
        """重置突破位"""
        self.breakout_high = 0
        self.breakout_low = 0
    
    def get_params(self) -> dict:
        """获取策略参数"""
        return {
            "name": "Momentum",
            "atr_period": self.atr_period,
            "atr_multiplier": self.atr_multiplier,
            "volume_ma_period": self.volume_ma_period,
            "volume_threshold": self.volume_threshold
        }
