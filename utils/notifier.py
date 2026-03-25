"""
通知模块
"""

import asyncio
import aiohttp
from typing import Dict


class Notifier:
    """通知模块"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.enabled = config.get("enabled", True)
        self.webhook_url = config.get("webhook_url", "")
        self.signal_threshold = config.get("signal_threshold", 0.8)
        
    async def send(self, message: str, level: str = "info"):
        """发送通知"""
        if not self.enabled:
            return
        
        # 飞书webhook通知
        if self.webhook_url:
            await self._send_webhook(message)
        
        # 打印到控制台
        print(f"[{level.upper()}] {message}")
        
    async def _send_webhook(self, message: str):
        """发送webhook通知"""
        if not self.webhook_url:
            return
            
        try:
            # 飞书机器人webhook
            if "open.feishu" in self.webhook_url:
                payload = {
                    "msg_type": "text",
                    "content": {
                        "text": f"【量化交易】{message}"
                    }
                }
            else:
                payload = {"text": message}
                
            async with aiohttp.ClientSession() as session:
                await session.post(self.webhook_url, json=payload)
                
        except Exception as e:
            print(f"Webhook发送失败: {e}")
    
    async def send_signal(self, signal: Dict):
        """发送交易信号通知"""
        symbol = signal.get("symbol", "")
        action = signal.get("action", "")
        reason = signal.get("reason", "")
        confidence = signal.get("confidence", 0)
        
        emoji = {
            "buy": "📈",
            "sell": "📉",
            "hold": "➡️"
        }.get(action, "❓")
        
        message = f"{emoji} {action.upper()} {symbol} | 置信度: {confidence:.0%} | {reason}"
        
        await self.send(message, level="info" if action == "hold" else "warning")
