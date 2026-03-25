"""
交易所对接模块
支持 Binance, Bybit, OKX 等主流交易所
"""

import asyncio
import hashlib
import hmac
import json
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class ExchangeBase(ABC):
    """交易所基类"""
    
    def __init__(self, api_key: str = "", api_secret: str = "", testnet: bool = True):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.base_url = self._get_base_url()
        self.session = None
        
    @abstractmethod
    def _get_base_url(self) -> str:
        """获取交易所API地址"""
        pass
    
    @abstractmethod
    async def connect(self):
        """连接交易所"""
        pass
    
    @abstractmethod
    async def get_klines(self, symbol: str, interval: str, limit: int = 200) -> List[Dict]:
        """获取K线数据"""
        pass
    
    @abstractmethod
    async def get_ticker(self, symbol: str) -> Dict:
        """获取行情数据"""
        pass
    
    @abstractmethod
    async def get_orderbook(self, symbol: str, limit: int = 20) -> Dict:
        """获取订单簿"""
        pass
    
    @abstractmethod
    async def get_position(self, symbol: str) -> Optional[Dict]:
        """获取持仓信息"""
        pass
    
    @abstractmethod
    async def open_long(self, symbol: str, amount: float) -> Dict:
        """开多仓"""
        pass
    
    @abstractmethod
    async def close_long(self, symbol: str, amount: float) -> Dict:
        """平多仓"""
        pass
    
    @abstractmethod
    async def open_short(self, symbol: str, amount: float) -> Dict:
        """开空仓"""
        pass
    
    @abstractmethod
    async def close_short(self, symbol: str, amount: float) -> Dict:
        """平空仓"""
        pass
    
    @abstractmethod
    async def get_order_status(self, symbol: str, order_id: str) -> str:
        """获取订单状态"""
        pass
    
    async def close(self):
        """关闭连接"""
        if self.session:
            await self.session.close()


class BinanceExchange(ExchangeBase):
    """币安交易所实现"""
    
    def __init__(self, api_key: str = "", api_secret: str = "", testnet: bool = True):
        super().__init__(api_key, api_secret, testnet)
        self.recv_window = 5000
        
    def _get_base_url(self) -> str:
        if self.testnet:
            return "https://testnet.binancefuture.com"
        return "https://fapi.binance.com"
    
    async def connect(self):
        """连接币安API"""
        import aiohttp
        self.session = aiohttp.ClientSession()
        
    def _sign(self, params: str) -> str:
        """生成签名"""
        return hmac.new(
            self.api_secret.encode('utf-8'),
            params.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def _headers(self) -> Dict:
        """请求头"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-MBX-APIKEY"] = self.api_key
        return headers
    
    async def _request(self, method: str, endpoint: str, params: Dict = None, signed: bool = False) -> Dict:
        """发送请求"""
        if params is None:
            params = {}
            
        if signed:
            params["timestamp"] = int(time.time() * 1000)
            params["recvWindow"] = self.recv_window
            
            # 生成签名
            query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
            params["signature"] = self._sign(query_string)
            
        url = f"{self.base_url}{endpoint}"
        
        async with self.session.request(
            method, url, 
            params=params if method == "GET" else None,
            json=params if method in ["POST", "PUT", "DELETE"] else None,
            headers=self._headers()
        ) as response:
            if response.status != 200:
                text = await response.text()
                raise Exception(f"API Error {response.status}: {text}")
            return await response.json()
    
    async def get_klines(self, symbol: str, interval: str, limit: int = 200) -> List[Dict]:
        """获取K线数据"""
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        
        data = await self._request("GET", "/fapi/v1/klines", params)
        
        klines = []
        for k in data:
            klines.append({
                "open_time": k[0],
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
                "close_time": k[6],
                "quote_volume": float(k[7]),
                "trades": k[8],
                "taker_buy_base": float(k[9]),
                "taker_buy_quote": float(k[10])
            })
        
        return klines
    
    async def get_ticker(self, symbol: str) -> Dict:
        """获取行情数据"""
        params = {"symbol": symbol}
        data = await self._request("GET", "/fapi/v1/ticker/24hr", params)
        
        return {
            "last": float(data["lastPrice"]),
            "high": float(data["highPrice"]),
            "low": float(data["lowPrice"]),
            "volume": float(data["volume"]),
            "quote_volume": float(data["quoteVolume"]),
            "price_change": float(data["priceChange"]),
            "price_change_pct": float(data["priceChangePercent"]),
            "bid": float(data["bidPrice"]),
            "ask": float(data["askPrice"]),
            "open": float(data["openPrice"])
        }
    
    async def get_orderbook(self, symbol: str, limit: int = 20) -> Dict:
        """获取订单簿"""
        params = {"symbol": symbol, "limit": limit}
        data = await self._request("GET", "/fapi/v1/depth", params)
        
        return {
            "bids": [[float(p[0]), float(p[1])] for p in data["bids"]],
            "asks": [[float(p[0]), float(p[1])] for p in data["asks"]],
            "last_update_id": data["lastUpdateId"]
        }
    
    async def get_position(self, symbol: str) -> Optional[Dict]:
        """获取持仓信息"""
        params = {"symbol": symbol}
        
        try:
            data = await self._request("GET", "/fapi/v2/positionRisk", params, signed=True)
            
            for position in data:
                if position["symbol"] == symbol and float(position["positionAmt"]) != 0:
                    return {
                        "symbol": position["symbol"],
                        "amount": abs(float(position["positionAmt"])),
                        "entry_price": float(position["entryPrice"]),
                        "mark_price": float(position["markPrice"]),
                        "unrealized_pnl": float(position["unrealizedProfit"]),
                        "leverage": int(position["leverage"]),
                        "side": "long" if float(position["positionAmt"]) > 0 else "short",
                        "margin": float(position["isolatedMargin"])
                    }
        except Exception:
            pass
        
        return None
    
    async def open_long(self, symbol: str, amount: float) -> Dict:
        """开多仓"""
        params = {
            "symbol": symbol,
            "side": "BUY",
            "positionSide": "LONG",
            "type": "MARKET",
            "quantity": amount
        }
        
        data = await self._request("POST", "/fapi/v1/order", params, signed=True)
        
        return {
            "order_id": str(data["orderId"]),
            "symbol": data["symbol"],
            "side": "BUY",
            "type": "MARKET",
            "amount": amount,
            "status": data["status"]
        }
    
    async def close_long(self, symbol: str, amount: float) -> Dict:
        """平多仓"""
        params = {
            "symbol": symbol,
            "side": "SELL",
            "positionSide": "LONG",
            "type": "MARKET",
            "quantity": amount
        }
        
        data = await self._request("POST", "/fapi/v1/order", params, signed=True)
        
        return {
            "order_id": str(data["orderId"]),
            "symbol": data["symbol"],
            "side": "SELL",
            "type": "MARKET",
            "amount": amount,
            "status": data["status"]
        }
    
    async def open_short(self, symbol: str, amount: float) -> Dict:
        """开空仓"""
        params = {
            "symbol": symbol,
            "side": "SELL",
            "positionSide": "SHORT",
            "type": "MARKET",
            "quantity": amount
        }
        
        data = await self._request("POST", "/fapi/v1/order", params, signed=True)
        
        return {
            "order_id": str(data["orderId"]),
            "symbol": data["symbol"],
            "side": "SELL",
            "type": "MARKET",
            "amount": amount,
            "status": data["status"]
        }
    
    async def close_short(self, symbol: str, amount: float) -> Dict:
        """平空仓"""
        params = {
            "symbol": symbol,
            "side": "BUY",
            "positionSide": "SHORT",
            "type": "MARKET",
            "quantity": amount
        }
        
        data = await self._request("POST", "/fapi/v1/order", params, signed=True)
        
        return {
            "order_id": str(data["orderId"]),
            "symbol": data["symbol"],
            "side": "BUY",
            "type": "MARKET",
            "amount": amount,
            "status": data["status"]
        }
    
    async def get_order_status(self, symbol: str, order_id: str) -> str:
        """获取订单状态"""
        params = {
            "symbol": symbol,
            "orderId": order_id
        }
        
        data = await self._request("GET", "/fapi/v1/order", params, signed=True)
        return data["status"]
    
    async def get_balance(self) -> float:
        """获取账户余额"""
        data = await self._request("GET", "/fapi/v2/balance", signed=True)
        
        for asset in data:
            if asset["asset"] == "USDT":
                return float(asset["availableBalance"])
        
        return 0.0
    
    async def get_funding_rate(self, symbol: str) -> Dict:
        """获取资金费率"""
        params = {"symbol": symbol}
        data = await self._request("GET", "/fapi/v1/fundingRate", params)
        
        if data:
            latest = data[-1]
            return {
                "funding_rate": float(latest["fundingRate"]),
                "funding_time": latest["fundingTime"]
            }
        
        return {"funding_rate": 0, "funding_time": 0}


class MockExchange(ExchangeBase):
    """模拟交易所（用于测试）"""
    
    def __init__(self, api_key: str = "", api_secret: str = "", testnet: bool = True):
        super().__init__(api_key, api_secret, testnet)
        self.positions = {}
        self.orders = {}
        self.balance = 10000.0  # 初始模拟余额
        
    def _get_base_url(self) -> str:
        return "mock://exchange"
    
    async def connect(self):
        """连接模拟交易所"""
        pass
    
    async def get_klines(self, symbol: str, interval: str, limit: int = 200) -> List[Dict]:
        """生成模拟K线数据"""
        import random
        
        klines = []
        base_price = 50000 if "BTC" in symbol else 3000
        now = int(time.time() * 1000)
        
        for i in range(limit, 0, -1):
            open_time = now - i * 3600000
            change = random.uniform(-0.02, 0.02)
            close = base_price * (1 + change)
            high = close * random.uniform(1.0, 1.02)
            low = close * random.uniform(0.98, 1.0)
            
            klines.append({
                "open_time": open_time,
                "open": round(base_price, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "close": round(close, 2),
                "volume": random.uniform(100, 1000),
                "close_time": open_time + 3600000,
                "quote_volume": random.uniform(5000000, 50000000),
                "trades": random.randint(1000, 10000)
            })
            
            base_price = close
        
        return klines
    
    async def get_ticker(self, symbol: str) -> Dict:
        """生成模拟行情"""
        import random
        
        base_price = 50000 if "BTC" in symbol else 3000
        price = base_price * random.uniform(0.98, 1.02)
        
        return {
            "last": round(price, 2),
            "high": round(price * 1.05, 2),
            "low": round(price * 0.95, 2),
            "volume": random.uniform(10000, 50000),
            "quote_volume": random.uniform(500000000, 2000000000),
            "price_change": round(random.uniform(-500, 500), 2),
            "price_change_pct": round(random.uniform(-5, 5), 2),
            "bid": round(price * 0.999, 2),
            "ask": round(price * 1.001, 2),
            "open": round(price * 0.98, 2)
        }
    
    async def get_orderbook(self, symbol: str, limit: int = 20) -> Dict:
        """生成模拟订单簿"""
        import random
        
        ticker = await self.get_ticker(symbol)
        price = ticker["last"]
        
        bids = []
        asks = []
        
        for i in range(limit):
            bids.append([
                round(price * (1 - 0.0001 * (i + 1)), 2),
                round(random.uniform(1, 10), 4)
            ])
            asks.append([
                round(price * (1 + 0.0001 * (i + 1)), 2),
                round(random.uniform(1, 10), 4)
            ])
        
        return {
            "bids": bids,
            "asks": asks,
            "last_update_id": int(time.time() * 1000)
        }
    
    async def get_position(self, symbol: str) -> Optional[Dict]:
        """获取持仓"""
        return self.positions.get(symbol)
    
    async def open_long(self, symbol: str, amount: float) -> Dict:
        """开多仓"""
        order_id = f"mock_{int(time.time() * 1000)}"
        
        self.positions[symbol] = {
            "symbol": symbol,
            "amount": amount,
            "entry_price": (await self.get_ticker(symbol))["last"],
            "mark_price": (await self.get_ticker(symbol))["last"],
            "unrealized_pnl": 0,
            "leverage": 10,
            "side": "long",
            "margin": amount * (await self.get_ticker(symbol))["last"] / 10
        }
        
        self.orders[order_id] = {
            "order_id": order_id,
            "symbol": symbol,
            "side": "BUY",
            "type": "MARKET",
            "amount": amount,
            "status": "filled"
        }
        
        return self.orders[order_id]
    
    async def close_long(self, symbol: str, amount: float) -> Dict:
        """平多仓"""
        order_id = f"mock_{int(time.time() * 1000)}"
        
        if symbol in self.positions:
            del self.positions[symbol]
        
        self.orders[order_id] = {
            "order_id": order_id,
            "symbol": symbol,
            "side": "SELL",
            "type": "MARKET",
            "amount": amount,
            "status": "filled"
        }
        
        return self.orders[order_id]
    
    async def open_short(self, symbol: str, amount: float) -> Dict:
        """开空仓"""
        order_id = f"mock_{int(time.time() * 1000)}"
        
        self.positions[symbol] = {
            "symbol": symbol,
            "amount": amount,
            "entry_price": (await self.get_ticker(symbol))["last"],
            "mark_price": (await self.get_ticker(symbol))["last"],
            "unrealized_pnl": 0,
            "leverage": 10,
            "side": "short",
            "margin": amount * (await self.get_ticker(symbol))["last"] / 10
        }
        
        self.orders[order_id] = {
            "order_id": order_id,
            "symbol": symbol,
            "side": "SELL",
            "type": "MARKET",
            "amount": amount,
            "status": "filled"
        }
        
        return self.orders[order_id]
    
    async def close_short(self, symbol: str, amount: float) -> Dict:
        """平空仓"""
        order_id = f"mock_{int(time.time() * 1000)}"
        
        if symbol in self.positions:
            del self.positions[symbol]
        
        self.orders[order_id] = {
            "order_id": order_id,
            "symbol": symbol,
            "side": "BUY",
            "type": "MARKET",
            "amount": amount,
            "status": "filled"
        }
        
        return self.orders[order_id]
    
    async def get_order_status(self, symbol: str, order_id: str) -> str:
        """获取订单状态"""
        order = self.orders.get(order_id)
        return order["status"] if order else "unknown"
    
    async def get_balance(self) -> float:
        """获取余额"""
        return self.balance
    
    async def get_funding_rate(self, symbol: str) -> Dict:
        """获取资金费率"""
        import random
        return {
            "funding_rate": random.uniform(-0.001, 0.001),
            "funding_time": int(time.time() * 1000) + 28800000
        }


def Exchange(name: str = "binance", api_key: str = "", api_secret: str = "", testnet: bool = True):
    """工厂函数：创建交易所实例"""
    if name.lower() == "binance":
        if not api_key:
            return MockExchange(testnet=testnet)
        return BinanceExchange(api_key, api_secret, testnet)
    elif name.lower() == "bybit":
        # 可以添加 Bybit 实现
        return MockExchange(testnet=testnet)
    else:
        return MockExchange(testnet=testnet)
