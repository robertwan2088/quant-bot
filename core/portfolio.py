"""
投资组合管理
"""

import time
from typing import Dict, List, Optional


class Portfolio:
    """投资组合管理"""
    
    def __init__(self, exchange, risk_config: dict):
        self.exchange = exchange
        self.risk_config = risk_config
        self.balance = 0.0
        self.initial_balance = 0.0
        self.positions = {}
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.trade_history = []
        
    async def update_balance(self):
        """更新余额"""
        self.balance = await self.exchange.get_balance()
        if self.initial_balance == 0:
            self.initial_balance = self.balance
    
    async def get_daily_pnl(self) -> float:
        """获取单日盈亏"""
        return self.daily_pnl
    
    def record_trade(self, trade: dict):
        """记录交易"""
        self.trade_history.append({
            **trade,
            "timestamp": time.time()
        })
        self.daily_trades += 1
        
        # 更新盈亏
        if trade.get("pnl"):
            self.daily_pnl += trade["pnl"]
    
    def get_total_value(self) -> float:
        """获取总价值"""
        position_value = sum(
            p.get("amount", 0) * p.get("mark_price", 0)
            for p in self.positions.values()
        )
        return self.balance + position_value
    
    def get_total_pnl(self) -> float:
        """获取总盈亏"""
        return self.get_total_value() - self.initial_balance
    
    def get_total_pnl_pct(self) -> float:
        """获取总盈亏比例"""
        if self.initial_balance == 0:
            return 0
        return self.get_total_pnl() / self.initial_balance
    
    def get_win_rate(self) -> float:
        """获取胜率"""
        if not self.trade_history:
            return 0
        
        wins = sum(1 for t in self.trade_history if t.get("pnl", 0) > 0)
        return wins / len(self.trade_history)
    
    def reset_daily(self):
        """重置每日统计"""
        self.daily_pnl = 0
        self.daily_trades = 0
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "balance": self.balance,
            "initial_balance": self.initial_balance,
            "total_value": self.get_total_value(),
            "total_pnl": self.get_total_pnl(),
            "total_pnl_pct": self.get_total_pnl_pct(),
            "daily_pnl": self.daily_pnl,
            "daily_trades": self.daily_trades,
            "win_rate": self.get_win_rate(),
            "positions_count": len(self.positions),
            "total_trades": len(self.trade_history)
        }
