"""
资金费率套利策略
利用期货与现货之间的资金费率差异获利
"""

import time
from typing import Dict, List


class FundingArbitrageStrategy:
    """资金费率套利策略"""
    
    def __init__(self, exchange, params: dict):
        self.exchange = exchange
        self.params = params
        
        # 策略参数
        self.min_funding_rate = params.get("min_funding_rate", 0.001)  # 最小资金费率
        self.rebalance_interval = params.get("rebalance_interval", 3600)  # 重新平衡间隔(秒)
        
        # 状态
        self.last_rebalance = 0
        self.current_funding = 0
        self.funding_history = []
        self.position_opened = False
        
    async def analyze(self, symbol: str, market: Dict) -> Dict:
        """分析市场并生成信号"""
        ticker = market.get("ticker", {})
        current_price = ticker.get("last", 0)
        
        if current_price == 0:
            return {"action": "hold", "reason": "价格数据无效"}
        
        # 获取资金费率
        try:
            funding_info = await self.exchange.get_funding_rate(symbol)
            funding_rate = funding_info.get("funding_rate", 0)
            funding_time = funding_info.get("funding_time", 0)
        except Exception:
            return {"action": "hold", "reason": "获取资金费率失败"}
        
        # 更新当前资金费率
        self.current_funding = funding_rate
        current_time = time.time()
        
        # 初始化结果
        result = {
            "action": "hold",
            "reason": "等待资金费率机会",
            "indicators": {}
        }
        
        # 记录资金费率历史
        self.funding_history.append({
            "rate": funding_rate,
            "time": current_time,
            "price": current_price
        })
        
        # 保持历史在100条以内
        if len(self.funding_history) > 100:
            self.funding_history = self.funding_history[-100:]
        
        # 资金费率历史平均
        avg_funding = sum(f["rate"] for f in self.funding_history) / len(self.funding_history) if self.funding_history else 0
        
        # 记录指标
        result["indicators"] = {
            "current_price": current_price,
            "funding_rate": funding_rate,
            "avg_funding": avg_funding,
            "funding_time": funding_time,
            "position_opened": self.position_opened,
            "time_to_funding": (funding_time / 1000 - current_time) if funding_time else 0
        }
        
        # 检查是否需要开仓
        if not self.position_opened:
            # 资金费率足够高，且高于历史平均
            if (funding_rate > self.min_funding_rate and 
                funding_rate > avg_funding * 1.5):
                
                # 计算预期收益
                # 假设每8小时结算一次资金费率
                daily_rate = funding_rate * 3  # 一天结算3次
                annualized_rate = daily_rate * 365
                
                result["action"] = "buy"
                result["reason"] = f"资金费率套利: 费率 {funding_rate*100:.4f}% (年化 {annualized_rate*100:.2f}%)"
                result["confidence"] = min(abs(funding_rate) / 0.01, 1.0)
                result["expected_rate"] = annualized_rate
                
        # 检查是否需要平仓
        else:
            # 资金费率变负或太低
            if funding_rate < -self.min_funding_rate:
                result["action"] = "sell"
                result["reason"] = f"资金费率转负: {funding_rate*100:.4f}%"
                result["confidence"] = 0.9
                
            # 定期再平衡
            elif current_time - self.last_rebalance > self.rebalance_interval:
                # 检查是否需要调整仓位
                if funding_rate < self.min_funding_rate * 0.5:
                    result["action"] = "sell"
                    result["reason"] = f"资金费率过低: {funding_rate*100:.4f}%"
                    result["confidence"] = 0.7
                    
                    # 重置状态
                    self.last_rebalance = current_time
        
        return result
    
    def open_position(self, symbol: str):
        """开仓"""
        self.position_opened = True
        self.last_rebalance = time.time()
    
    def close_position(self, symbol: str):
        """平仓"""
        self.position_opened = False
        self.last_rebalance = time.time()
    
    def get_params(self) -> dict:
        """获取策略参数"""
        return {
            "name": "FundingArbitrage",
            "min_funding_rate": self.min_funding_rate,
            "rebalance_interval": self.rebalance_interval
        }
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        if not self.funding_history:
            return {
                "avg_funding": 0,
                "max_funding": 0,
                "min_funding": 0,
                "total_earnings": 0
            }
        
        rates = [f["rate"] for f in self.funding_history]
        
        return {
            "avg_funding": sum(rates) / len(rates),
            "max_funding": max(rates),
            "min_funding": min(rates),
            "current_funding": self.current_funding,
            "position_opened": self.position_opened,
            "samples": len(rates)
        }
