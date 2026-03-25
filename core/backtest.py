"""
回测模块
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List
import pandas as pd
import numpy as np


class Backtester:
    """回测引擎"""
    
    def __init__(self, exchange, strategy, config: dict):
        self.exchange = exchange
        self.strategy = strategy
        self.config = config
        
        # 回测结果
        self.trades = []
        self.equity_curve = []
        self.initial_balance = config.get("initial_balance", 10000)
        self.current_balance = self.initial_balance
        self.position = None
        self.position_history = []
        
    async def run(self, symbol: str, start_time: str, end_time: str, interval: str = "1h") -> Dict:
        """运行回测"""
        # 转换时间
        start_ts = int(datetime.fromisoformat(start_time.replace("Z", "+00:00")).timestamp() * 1000)
        end_ts = int(datetime.fromisoformat(end_time.replace("Z", "+00:00")).timestamp() * 1000)
        
        # 获取历史数据
        klines = await self.exchange.get_klines(symbol, interval, 2000)
        
        # 过滤时间范围
        klines = [k for k in klines if start_ts <= k['open_time'] <= end_ts]
        
        if len(klines) < 100:
            return {"error": "数据不足"}
        
        # 模拟交易
        self.trades = []
        self.equity_curve = []
        self.current_balance = self.initial_balance
        self.position = None
        
        total_steps = len(klines)
        
        for i in range(50, total_steps):  # 前面50根K线用于计算指标
            current_kline = klines[i]
            historical_klines = klines[:i+1]
            
            # 构建市场数据
            market = {
                "klines": historical_klines,
                "ticker": {
                    "last": current_kline['close'],
                    "high": current_kline['high'],
                    "low": current_kline['low'],
                    "volume": current_kline['volume']
                }
            }
            
            # 获取策略信号
            signal = await self.strategy.analyze(symbol, market)
            
            # 执行交易
            await self._execute_signal(symbol, signal, current_kline)
            
            # 记录权益
            self._record_equity(current_kline, current_kline['close_time'])
        
        # 计算统计
        stats = self._calculate_stats()
        
        return {
            "symbol": symbol,
            "period": f"{start_time} ~ {end_time}",
            "initial_balance": self.initial_balance,
            "final_balance": self.current_balance,
            "total_return": (self.current_balance - self.initial_balance) / self.initial_balance,
            "stats": stats,
            "trades": self.trades,
            "equity_curve": self.equity_curve
        }
    
    async def _execute_signal(self, symbol: str, signal: dict, kline: dict):
        """执行信号"""
        action = signal.get("action")
        price = kline['close']
        
        if action == "buy" and self.position is None:
            # 开多仓
            amount = self.current_balance * 0.1 / price  # 10%仓位
            self.position = {
                "side": "long",
                "amount": amount,
                "entry_price": price,
                "entry_time": kline['open_time']
            }
            self.current_balance -= amount * price
            
            self.trades.append({
                "time": kline['open_time'],
                "action": "buy",
                "price": price,
                "amount": amount,
                "reason": signal.get("reason", "")
            })
            
        elif action == "sell" and self.position and self.position["side"] == "long":
            # 平多仓
            pnl = (price - self.position["entry_price"]) * self.position["amount"]
            self.current_balance += self.position["amount"] * price + pnl
            
            self.trades.append({
                "time": kline['open_time'],
                "action": "sell",
                "price": price,
                "amount": self.position["amount"],
                "pnl": pnl,
                "reason": signal.get("reason", "")
            })
            
            self.position = None
            
        elif action == "sell" and self.position is None:
            # 开空仓
            amount = self.current_balance * 0.1 / price
            self.position = {
                "side": "short",
                "amount": amount,
                "entry_price": price,
                "entry_time": kline['open_time']
            }
            self.current_balance += amount * price  # 空仓获得资金
            
            self.trades.append({
                "time": kline['open_time'],
                "action": "sell_short",
                "price": price,
                "amount": amount,
                "reason": signal.get("reason", "")
            })
            
        elif action == "buy" and self.position and self.position["side"] == "short":
            # 平空仓
            pnl = (self.position["entry_price"] - price) * self.position["amount"]
            self.current_balance += self.position["amount"] * price + pnl
            
            self.trades.append({
                "time": kline['open_time'],
                "action": "buy_cover",
                "price": price,
                "amount": self.position["amount"],
                "pnl": pnl,
                "reason": signal.get("reason", "")
            })
            
            self.position = None
    
    def _record_equity(self, kline: dict, timestamp: int):
        """记录权益曲线"""
        equity = self.current_balance
        
        if self.position:
            if self.position["side"] == "long":
                equity += self.position["amount"] * kline['close']
            else:
                # 空仓：保证金 + 盈亏
                equity = self.current_balance + self.position["amount"] * (
                    self.position["entry_price"] - kline['close']
                )
        
        self.equity_curve.append({
            "time": timestamp,
            "equity": equity
        })
    
    def _calculate_stats(self) -> Dict:
        """计算统计指标"""
        if not self.trades:
            return {}
        
        closed_trades = [t for t in self.trades if "pnl" in t]
        
        if not closed_trades:
            return {"total_trades": 0}
        
        pnls = [t["pnl"] for t in closed_trades]
        
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        
        total_trades = len(closed_trades)
        win_count = len(wins)
        loss_count = len(losses)
        
        win_rate = win_count / total_trades if total_trades > 0 else 0
        
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        
        max_drawdown = self._calculate_max_drawdown()
        
        # 夏普比率（简化）
        returns = [(self.equity_curve[i+1]["equity"] - self.equity_curve[i]["equity"]) / self.equity_curve[i]["equity"] 
                   for i in range(len(self.equity_curve)-1) if self.equity_curve[i]["equity"] > 0]
        sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252) if len(returns) > 1 and np.std(returns) > 0 else 0
        
        return {
            "total_trades": total_trades,
            "winning_trades": win_count,
            "losing_trades": loss_count,
            "win_rate": win_rate,
            "total_pnl": sum(pnls),
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else 0,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe,
            "max_equity": max(e["equity"] for e in self.equity_curve) if self.equity_curve else self.initial_balance,
            "min_equity": min(e["equity"] for e in self.equity_curve) if self.equity_curve else self.initial_balance
        }
    
    def _calculate_max_drawdown(self) -> float:
        """计算最大回撤"""
        if not self.equity_curve:
            return 0
        
        peak = self.equity_curve[0]["equity"]
        max_dd = 0
        
        for point in self.equity_curve:
            if point["equity"] > peak:
                peak = point["equity"]
            
            dd = (peak - point["equity"]) / peak
            if dd > max_dd:
                max_dd = dd
        
        return max_dd
    
    def get_trade_history(self) -> List[Dict]:
        """获取交易历史"""
        return self.trades
    
    def get_equity_curve(self) -> List[Dict]:
        """获取权益曲线"""
        return self.equity_curve


async def run_backtest(symbol: str, strategy_name: str, start_date: str, end_date: str, 
                       exchange_name: str = "binance", initial_balance: float = 10000) -> Dict:
    """快速回测函数"""
    from core.exchange import Exchange
    
    # 创建模拟交易所
    exchange = Exchange(exchange_name, testnet=True)
    await exchange.connect()
    
    # 创建策略
    strategy = None
    if strategy_name == "trend_following":
        from strategies.trend_following import TrendFollowingStrategy
        strategy = TrendFollowingStrategy(exchange, {})
    elif strategy_name == "grid":
        from strategies.grid_trading import GridTradingStrategy
        strategy = GridTradingStrategy(exchange, {})
    elif strategy_name == "momentum":
        from strategies.momentum import MomentumStrategy
        strategy = MomentumStrategy(exchange, {})
    
    if not strategy:
        return {"error": f"未知策略: {strategy_name}"}
    
    # 运行回测
    config = {"initial_balance": initial_balance}
    backtester = Backtester(exchange, strategy, config)
    
    result = await backtester.run(symbol, start_date, end_date)
    
    await exchange.close()
    
    return result
