#!/usr/bin/env python3
"""
数字货币量化交易系统
支持 USDT 本位合约交易
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import yaml

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.exchange import Exchange
from core.portfolio import Portfolio
from strategies.trend_following import TrendFollowingStrategy
from strategies.grid_trading import GridTradingStrategy
from strategies.momentum import MomentumStrategy
from strategies.funding_arbitrage import FundingArbitrageStrategy
from utils.notifier import Notifier
from utils.logger import setup_logger


class TradingBot:
    """量化交易主程序"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config = self._load_config(config_path)
        self.logger = setup_logger("TradingBot", self.config.get("logging", {}))
        self.exchange = None
        self.portfolio = None
        self.strategies = {}
        self.notifier = Notifier(self.config.get("notifications", {}))
        self.running = False
        self.positions = {}
        self.orders = {}
        self.signals = {}
        self.market_data = {}  # 添加市场数据存储
        
    def _load_config(self, config_path: str) -> dict:
        """加载配置文件"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    async def initialize(self):
        """初始化交易系统"""
        self.logger.info("=" * 50)
        self.logger.info("🚀 量化交易系统启动")
        self.logger.info("=" * 50)
        
        # 初始化交易所连接
        exchange_config = self.config.get("exchange", {})
        self.exchange = Exchange(
            name=exchange_config.get("name", "binance"),
            api_key=exchange_config.get("api_key", ""),
            api_secret=exchange_config.get("api_secret", ""),
            testnet=exchange_config.get("testnet", True)
        )
        await self.exchange.connect()
        
        # 初始化投资组合
        self.portfolio = Portfolio(self.exchange, self.config.get("risk", {}))
        await self.portfolio.update_balance()
        
        # 初始化策略
        await self._init_strategies()
        
        # 加载当前持仓
        await self._load_positions()
        
        self.logger.info(f"✅ 初始化完成 | 账户余额: {self.portfolio.balance:.2f} USDT")
    
    async def _init_strategies(self):
        """初始化交易策略"""
        strategies_config = self.config.get("strategies", {})
        
        if strategies_config.get("trend_following", {}).get("enabled"):
            self.strategies["trend_following"] = TrendFollowingStrategy(
                self.exchange,
                strategies_config["trend_following"]["params"]
            )
            self.logger.info("✅ 趋势跟踪策略已加载")
        
        if strategies_config.get("grid_trading", {}).get("enabled"):
            self.strategies["grid_trading"] = GridTradingStrategy(
                self.exchange,
                strategies_config["grid_trading"]["params"]
            )
            self.logger.info("✅ 网格交易策略已加载")
            
        if strategies_config.get("momentum", {}).get("enabled"):
            self.strategies["momentum"] = MomentumStrategy(
                self.exchange,
                strategies_config["momentum"]["params"]
            )
            self.logger.info("✅ 动量突破策略已加载")
            
        if strategies_config.get("funding_arbitrage", {}).get("enabled"):
            self.strategies["funding_arbitrage"] = FundingArbitrageStrategy(
                self.exchange,
                strategies_config["funding_arbitrage"]["params"]
            )
            self.logger.info("✅ 资金费率套利策略已加载")
    
    async def _load_positions(self):
        """加载当前持仓"""
        symbols = self.config.get("symbols", ["BTCUSDT", "ETHUSDT"])
        for symbol in symbols:
            position = await self.exchange.get_position(symbol)
            if position:
                self.positions[symbol] = position
    
    async def start(self):
        """启动交易系统"""
        await self.initialize()
        self.running = True
        
        self.logger.info("🔄 开始交易循环...")
        
        # 主交易循环
        while self.running:
            try:
                # 更新市场数据
                await self._update_market_data()
                
                # 执行策略信号
                await self._execute_strategies()
                
                # 检查风控
                await self._check_risk()
                
                # 清理已完成订单
                await self._cleanup_orders()
                
                # 等待下一个周期
                await asyncio.sleep(60)  # 1分钟执行一次
                
            except Exception as e:
                self.logger.error(f"❌ 交易循环错误: {e}")
                await asyncio.sleep(60)
    
    async def _update_market_data(self):
        """更新市场数据"""
        symbols = self.config.get("symbols", ["BTCUSDT", "ETHUSDT"])
        
        for symbol in symbols:
            try:
                # 获取K线数据
                klines = await self.exchange.get_klines(symbol, "1h", 200)
                
                # 获取当前价格
                ticker = await self.exchange.get_ticker(symbol)
                
                # 获取订单簿
                orderbook = await self.exchange.get_orderbook(symbol)
                
                # 存储数据
                self.market_data[symbol] = {
                    "klines": klines,
                    "ticker": ticker,
                    "orderbook": orderbook,
                    "timestamp": datetime.now()
                }
                
            except Exception as e:
                self.logger.error(f"获取{symbol}市场数据失败: {e}")
    
    async def _execute_strategies(self):
        """执行所有策略"""
        for strategy_name, strategy in self.strategies.items():
            try:
                # 获取对应交易对的市场数据
                symbols = self.config.get("symbols", ["BTCUSDT", "ETHUSDT"])
                
                for symbol in symbols:
                    if symbol not in self.market_data:
                        continue
                    
                    market = self.market_data[symbol]
                    
                    # 生成交易信号
                    signal = await strategy.analyze(symbol, market)
                    
                    if signal and signal.get("action") != "hold":
                        # 计算信号强度
                        signal_strength = self._calculate_signal_strength(signal)
                        
                        if signal_strength >= self.config.get("notifications", {}).get("signal_threshold", 0.8):
                            self.signals[symbol] = {
                                "strategy": strategy_name,
                                "signal": signal,
                                "strength": signal_strength,
                                "timestamp": datetime.now()
                            }
                            
                            # 执行交易
                            await self._execute_trade(symbol, signal)
                            
            except Exception as e:
                self.logger.error(f"执行策略{strategy_name}失败: {e}")
    
    def _calculate_signal_strength(self, signal: dict) -> float:
        """计算信号强度"""
        action = signal.get("action")
        if action == "hold":
            return 0.0
        
        # 基于多个指标计算信号强度
        strength = 0.5  # 基础强度
        
        if signal.get("indicators", {}).get("trend") == "up":
            strength += 0.2
        elif signal.get("indicators", {}).get("trend") == "down":
            strength -= 0.2
            
        if signal.get("indicators", {}).get("momentum") > 0:
            strength += 0.15
            
        if signal.get("indicators", {}).get("volume_confirm"):
            strength += 0.15
            
        return max(0, min(1, strength))
    
    async def _execute_trade(self, symbol: str, signal: dict):
        """执行交易"""
        action = signal.get("action")
        
        # 检查当前持仓
        current_position = self.positions.get(symbol, {})
        position_side = current_position.get("side", "none")
        
        # 检查是否需要开仓
        if action == "buy" and position_side == "none":
            # 开多仓
            amount = self._calculate_position_size(symbol)
            order = await self.exchange.open_long(symbol, amount)
            self.orders[order["order_id"]] = order
            self.logger.info(f"📈 开多仓 {symbol} {amount}")
            await self.notifier.send(f"开多仓信号: {symbol}, 数量: {amount}")
            
        elif action == "sell" and position_side == "long":
            # 平多仓
            amount = current_position.get("amount", 0)
            order = await self.exchange.close_long(symbol, amount)
            self.orders[order["order_id"]] = order
            self.logger.info(f"📉 平多仓 {symbol}")
            await self.notifier.send(f"平多仓信号: {symbol}")
            
        elif action == "sell_short" and position_side == "none":
            # 开空仓
            amount = self._calculate_position_size(symbol)
            order = await self.exchange.open_short(symbol, amount)
            self.orders[order["order_id"]] = order
            self.logger.info(f"📉 开空仓 {symbol} {amount}")
            await self.notifier.send(f"开空仓信号: {symbol}, 数量: {amount}")
            
        elif action == "buy_cover" and position_side == "short":
            # 平空仓
            amount = current_position.get("amount", 0)
            order = await self.exchange.close_short(symbol, amount)
            self.orders[order["order_id"]] = order
            self.logger.info(f"📈 平空仓 {symbol}")
            await self.notifier.send(f"平空仓信号: {symbol}")
    
    def _calculate_position_size(self, symbol: str) -> float:
        """计算仓位大小"""
        risk_config = self.config.get("risk", {})
        max_position_pct = risk_config.get("max_position_pct", 0.3)
        max_leverage = risk_config.get("max_leverage", 50)
        
        # 获取当前价格
        ticker = self.market_data.get(symbol, {}).get("ticker", {})
        current_price = ticker.get("last", 50000)
        
        # 计算可用保证金
        available_balance = self.portfolio.balance * max_position_pct
        
        # 计算仓位大小
        position_size = (available_balance * max_leverage) / current_price
        
        # 保留两位小数
        return round(position_size, 4)
    
    async def _check_risk(self):
        """检查风控"""
        risk_config = self.config.get("risk", {})
        
        # 检查持仓比例
        for symbol, position in self.positions.items():
            position_pct = position.get("amount", 0) * position.get("entry_price", 0) / self.portfolio.balance
            if position_pct > risk_config.get("max_position_pct", 0.3):
                self.logger.warning(f"⚠️ {symbol} 持仓比例过高: {position_pct:.2%}")
        
        # 检查单日亏损
        daily_pnl = await self.portfolio.get_daily_pnl()
        if daily_pnl < -risk_config.get("max_daily_loss_pct", 0.05) * self.portfolio.balance:
            self.logger.warning("⚠️ 达到单日最大亏损，暂停交易")
            # 可以添加自动平仓逻辑
    
    async def _cleanup_orders(self):
        """清理已完成订单"""
        completed_orders = []
        
        for order_id, order in self.orders.items():
            status = await self.exchange.get_order_status(order["symbol"], order_id)
            
            if status in ["filled", "cancelled", "rejected"]:
                completed_orders.append(order_id)
                
                # 更新持仓信息
                if status == "filled":
                    await self._update_position(order["symbol"])
        
        # 移除已完成订单
        for order_id in completed_orders:
            del self.orders[order_id]
    
    async def _update_position(self, symbol: str):
        """更新持仓信息"""
        position = await self.exchange.get_position(symbol)
        if position:
            self.positions[symbol] = position
    
    async def stop(self):
        """停止交易系统"""
        self.logger.info("🛑 正在停止交易系统...")
        self.running = False
        
        # 平掉所有仓位
        for symbol, position in self.positions.items():
            if position.get("amount", 0) > 0:
                if position.get("side") == "long":
                    await self.exchange.close_long(symbol, position["amount"])
                elif position.get("side") == "short":
                    await self.exchange.close_short(symbol, position["amount"])
        
        # 关闭交易所连接
        if self.exchange:
            await self.exchange.close()
        
        self.logger.info("✅ 交易系统已停止")
    
    def get_status(self) -> dict:
        """获取系统状态"""
        return {
            "running": self.running,
            "strategies": list(self.strategies.keys()),
            "positions": self.positions,
            "balance": self.portfolio.balance if self.portfolio else 0,
            "signals": self.signals,
            "orders_count": len(self.orders)
        }


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="数字货币量化交易系统")
    parser.add_argument("-c", "--config", default="config/config.yaml", help="配置文件路径")
    parser.add_argument("--web", action="store_true", help="启动Web界面")
    parser.add_argument("--port", type=int, default=8080, help="Web服务端口")
    
    args = parser.parse_args()
    
    # 创建交易机器人
    bot = TradingBot(args.config)
    
    if args.web:
        # 启动Web界面
        from web.app import create_app
        app = create_app(bot)
        app.run(host="0.0.0.0", port=args.port, debug=False)
    else:
        # 启动交易
        try:
            await bot.start()
        except KeyboardInterrupt:
            await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
