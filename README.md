# 量化交易系统

USDT本位合约量化交易系统，支持BTC、ETH等主流币种。

## 功能特性

### 交易策略

1. **趋势跟踪策略 (Trend Following)**
   - 均线交叉信号（快线/慢线）
   - RSI超买超卖判断
   - 布林带突破识别
   - 成交量确认

2. **网格交易策略 (Grid Trading)**
   - 自动化高抛低吸
   - 智能网格重平衡
   - 适合震荡行情

3. **动量突破策略 (Momentum)**
   - ATR动态止损
   - 成交量突破识别
   - 20日高低点突破

4. **资金费率套利 (Funding Arbitrage)**
   - 期货现货资金费率差
   - 自动套利机会识别
   - 低风险稳定收益

### 风控管理

- 仓位比例控制
- 止损止盈设置
- 单日最大亏损限制
- 杠杆倍数限制

### 可视化界面

- 实时账户状态
- 盈亏曲线图表
- 持仓管理
- 交易信号记录

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

编辑 `config/config.yaml`：

```yaml
exchange:
  name: binance
  testnet: true  # 测试网
  api_key: your_api_key
  api_secret: your_api_secret

symbols:
  - BTCUSDT
  - ETHUSDT

strategies:
  trend_following:
    enabled: true
```

### 3. 运行

```bash
# 模拟交易（测试）
python main.py

# 启动Web界面
python main.py --web --port 8080

# 真实交易
# 将 config.yaml 中的 testnet 改为 false，并填入真实API
```

## Web界面

启动后访问 http://localhost:8080

功能：
- 查看账户余额和盈亏
- 实时持仓监控
- 交易信号记录
- 启动/停止交易

## 策略说明

### 趋势跟踪

**原理**：当短期均线上穿长期均线时买入，下穿时卖出

**参数**：
- fast_ma_period: 快速均线周期（默认10）
- slow_ma_period: 慢速均线周期（默认50）
- rsi_period: RSI周期（默认14）

### 网格交易

**原理**：在价格区间内设置多个网格，每个网格低买高卖

**参数**：
- grid_levels: 网格层数（默认10）
- price_range: 价格波动范围（默认5%）
- grid_spacing: 网格间距（默认0.5%）

### 动量突破

**原理**：当价格突破20日高点且成交量放大时买入

**参数**：
- atr_period: ATR周期（默认14）
- atr_multiplier: ATR倍数（默认2）
- volume_threshold: 成交量阈值（默认1.5倍）

### 资金费率套利

**原理**：利用期货合约与现货之间的资金费率差异获利

**参数**：
- min_funding_rate: 最小资金费率（默认0.1%）
- rebalance_interval: 重新平衡间隔（默认1小时）

## 注意事项

1. **风险提示**：量化交易存在风险，请先用模拟盘测试
2. **API安全**：不要将API Secret提交到公开仓库
3. **风控设置**：建议根据自身风险承受能力调整风控参数
4. **监控**：建议定期检查交易日志和持仓情况

## 目录结构

```
quant-bot/
├── config/
│   └── config.yaml          # 配置文件
├── core/
│   ├── exchange.py          # 交易所对接
│   └── portfolio.py         # 投资组合管理
├── strategies/
│   ├── trend_following.py   # 趋势跟踪
│   ├── grid_trading.py      # 网格交易
│   ├── momentum.py         # 动量突破
│   └── funding_arbitrage.py # 资金费率套利
├── web/
│   └── app.py               # Web界面
├── utils/
│   ├── notifier.py          # 通知模块
│   └── logger.py            # 日志模块
├── main.py                  # 主程序
└── requirements.txt         # 依赖
```

## 技术栈

- Python 3.8+
- Flask (Web界面)
- aiohttp (异步HTTP)
- pandas (数据分析)
- numpy (数值计算)
- pyyaml (配置文件)

## 免责声明

本系统仅供学习和研究使用，不构成投资建议。使用本系统造成的任何损失，用户自行承担。
