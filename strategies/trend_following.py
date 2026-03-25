"""
趋势跟踪策略
结合均线交叉、RSI、布林带指标
"""

from typing import Dict, List
import pandas as pd
import numpy as np


class TrendFollowingStrategy:
    """趋势跟踪策略"""
    
    def __init__(self, exchange, params: dict):
        self.exchange = exchange
        self.params = params
        
        # 策略参数
        self.fast_ma_period = params.get("fast_ma_period", 10)
        self.slow_ma_period = params.get("slow_ma_period", 50)
        self.rsi_period = params.get("rsi_period", 14)
        self.rsi_overbought = params.get("rsi_overbought", 70)
        self.rsi_oversold = params.get("rsi_oversold", 30)
        self.bb_period = params.get("bb_period", 20)
        self.bb_std = params.get("bb_std", 2)
        
    def calculate_indicators(self, klines: List[Dict]) -> Dict:
        """计算技术指标"""
        if not klines or len(klines) < self.slow_ma_period + self.bb_period:
            return {}
        
        # 转换为DataFrame
        df = pd.DataFrame(klines)
        df['close'] = df['close'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['volume'] = df['volume'].astype(float)
        
        # 计算移动平均线
        df['fast_ma'] = df['close'].rolling(window=self.fast_ma_period).mean()
        df['slow_ma'] = df['close'].rolling(window=self.slow_ma_period).mean()
        
        # 计算RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 计算布林带
        df['bb_middle'] = df['close'].rolling(window=self.bb_period).mean()
        bb_std = df['close'].rolling(window=self.bb_period).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * self.bb_std)
        df['bb_lower'] = df['bb_middle'] - (bb_std * self.bb_std)
        
        # 计算ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(window=14).mean()
        
        # 计算成交量均线
        df['volume_ma'] = df['volume'].rolling(window=20).mean()
        
        return df
    
    async def analyze(self, symbol: str, market: Dict) -> Dict:
        """分析市场并生成信号"""
        klines = market.get("klines", [])
        
        if not klines or len(klines) < self.slow_ma_period + 10:
            return {"action": "hold", "reason": "数据不足"}
        
        df = self.calculate_indicators(klines)
        
        # 获取最新数据
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        current_price = last['close']
        fast_ma = last['fast_ma']
        slow_ma = last['slow_ma']
        prev_fast_ma = prev['fast_ma']
        prev_slow_ma = prev['slow_ma']
        rsi = last['rsi']
        
        # 初始化结果
        result = {
            "action": "hold",
            "reason": "无明确信号",
            "indicators": {}
        }
        
        # 均线交叉信号
        ma_signal = "hold"
        
        # 金叉（多头信号）
        if prev_fast_ma <= prev_slow_ma and fast_ma > slow_ma:
            ma_signal = "buy"
        # 死叉（空头信号）
        elif prev_fast_ma >= prev_slow_ma and fast_ma < slow_ma:
            ma_signal = "sell"
        
        # RSI信号
        rsi_signal = "hold"
        if rsi < self.rsi_oversold:
            rsi_signal = "buy"
        elif rsi > self.rsi_overbought:
            rsi_signal = "sell"
        
        # 布林带信号
        bb_signal = "hold"
        if current_price < last['bb_lower']:
            bb_signal = "buy"  # 超卖
        elif current_price > last['bb_upper']:
            bb_signal = "sell"  # 超买
        
        # 综合信号
        buy_signals = sum([
            ma_signal == "buy",
            rsi_signal == "buy",
            bb_signal == "buy"
        ])
        
        sell_signals = sum([
            ma_signal == "sell",
            rsi_signal == "sell",
            bb_signal == "sell"
        ])
        
        # 成交量确认
        volume_confirm = last['volume'] > last['volume_ma']
        
        # 记录指标
        result["indicators"] = {
            "price": current_price,
            "fast_ma": fast_ma,
            "slow_ma": slow_ma,
            "rsi": rsi,
            "bb_position": (current_price - last['bb_lower']) / (last['bb_upper'] - last['bb_lower']) if last['bb_upper'] != last['bb_lower'] else 0.5,
            "volume_ratio": last['volume'] / last['volume_ma'] if last['volume_ma'] > 0 else 1,
            "volume_confirm": volume_confirm,
            "trend": "up" if fast_ma > slow_ma else "down",
            "ma_signal": ma_signal,
            "rsi_signal": rsi_signal,
            "bb_signal": bb_signal,
            "momentum": (current_price - df.iloc[-10]['close']) / df.iloc[-10]['close'] if len(df) >= 10 else 0
        }
        
        # 决定交易动作
        # 做多条件：均线多头+RSI不过热+成交量确认
        if buy_signals >= 2 and volume_confirm and fast_ma > slow_ma:
            result["action"] = "buy"
            result["reason"] = f"多头信号: MA({buy_signals > 0}) + RSI({rsi_signal}) + BB({bb_signal})"
            result["confidence"] = min(buy_signals / 3 + 0.2, 1.0)
        
        # 做空条件：均线空头+RSI不过冷+成交量确认
        elif sell_signals >= 2 and volume_confirm and fast_ma < slow_ma:
            result["action"] = "sell"
            result["reason"] = f"空头信号: MA({sell_signals > 0}) + RSI({rsi_signal}) + BB({bb_signal})"
            result["confidence"] = min(sell_signals / 3 + 0.2, 1.0)
        
        # 止盈止损检查（如果已有持仓）
        # 这部分在实际运行时会结合持仓信息
        
        return result
    
    def get_params(self) -> dict:
        """获取策略参数"""
        return {
            "name": "TrendFollowing",
            "fast_ma_period": self.fast_ma_period,
            "slow_ma_period": self.slow_ma_period,
            "rsi_period": self.rsi_period,
            "rsi_overbought": self.rsi_overbought,
            "rsi_oversold": self.rsi_oversold,
            "bb_period": self.bb_period,
            "bb_std": self.bb_std
        }
