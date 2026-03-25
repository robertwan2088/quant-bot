"""
网格交易策略
在震荡行情中自动进行高抛低吸
"""

import time
from typing import Dict, List


class GridTradingStrategy:
    """网格交易策略"""
    
    def __init__(self, exchange, params: dict):
        self.exchange = exchange
        self.params = params
        
        # 策略参数
        self.grid_levels = params.get("grid_levels", 10)
        self.price_range = params.get("price_range", 0.05)  # 5%
        self.grid_spacing = params.get("grid_spacing", 0.005)  # 0.5%
        self.order_amount = params.get("order_amount", 100)  # USDT
        
        # 状态
        self.grid_prices = []
        self.orders = {}
        self.base_price = 0
        self.last_rebalance_time = 0
        
    async def analyze(self, symbol: str, market: Dict) -> Dict:
        """分析市场并生成信号"""
        ticker = market.get("ticker", {})
        current_price = ticker.get("last", 0)
        
        if current_price == 0:
            return {"action": "hold", "reason": "价格数据无效"}
        
        # 初始化网格
        if not self.grid_prices:
            self.base_price = current_price
            self._init_grid(current_price)
            return {
                "action": "hold",
                "reason": "网格初始化",
                "grid": self.grid_prices
            }
        
        # 检查是否需要重新平衡
        price_change = abs(current_price - self.base_price) / self.base_price
        
        if price_change > self.price_range:
            # 价格突破范围，重新平衡网格
            self._rebalance_grid(current_price)
            return {
                "action": "hold",
                "reason": "网格重新平衡",
                "grid": self.grid_prices
            }
        
        # 检查网格订单
        signals = self._check_grid_orders(current_price)
        
        if signals:
            return signals
        
        return {"action": "hold", "reason": "网格内波动"}
    
    def _init_grid(self, base_price: float):
        """初始化网格"""
        self.grid_prices = []
        
        # 生成上下网格价格
        for i in range(-self.grid_levels // 2, self.grid_levels // 2 + 1):
            price = base_price * (1 + i * self.grid_spacing)
            self.grid_prices.append({
                "price": price,
                "level": i,
                "buy_order": None,
                "sell_order": None,
                "filled": False
            })
    
    def _rebalance_grid(self, new_price: float):
        """重新平衡网格"""
        # 取消所有未完成订单
        # 这里需要调用exchange取消订单
        
        # 重置网格
        self.grid_prices = []
        self.base_price = new_price
        self._init_grid(new_price)
    
    def _check_grid_orders(self, current_price: float) -> Dict:
        """检查网格订单触发"""
        # 找到当前价格所在的网格
        for grid in self.grid_prices:
            grid_price = grid["price"]
            
            # 价格触及买入网格
            if (current_price <= grid_price * (1 + 0.001) and 
                current_price >= grid_price * (1 - 0.001) and 
                not grid.get("buy_filled")):
                
                return {
                    "action": "buy",
                    "reason": f"网格买入 L{grid['level']}",
                    "grid_level": grid["level"],
                    "price": grid_price,
                    "amount": self.order_amount / current_price,
                    "strategy": "grid"
                }
            
            # 价格触及卖出网格
            if (current_price >= grid_price * (1 - 0.001) and 
                current_price <= grid_price * (1 + 0.001) and 
                grid.get("buy_filled") and 
                not grid.get("sell_filled")):
                
                return {
                    "action": "sell",
                    "reason": f"网格卖出 L{grid['level']}",
                    "grid_level": grid["level"],
                    "price": grid_price,
                    "amount": self.order_amount / grid_price,
                    "strategy": "grid"
                }
        
        return {}
    
    def get_params(self) -> dict:
        """获取策略参数"""
        return {
            "name": "GridTrading",
            "grid_levels": self.grid_levels,
            "price_range": self.price_range,
            "grid_spacing": self.grid_spacing,
            "order_amount": self.order_amount
        }
    
    def get_status(self) -> dict:
        """获取网格状态"""
        return {
            "base_price": self.base_price,
            "grid_prices": len(self.grid_prices),
            "active_orders": len(self.orders)
        }
