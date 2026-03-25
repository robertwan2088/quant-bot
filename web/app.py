"""
Web可视化界面 - 完整版
"""

from flask import Flask, jsonify, render_template_string, request
import threading
import time
import asyncio
from datetime import datetime, timedelta


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>量化交易系统</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0a1a; color: #e0e0e0; min-height: 100vh;
        }
        .container { max-width: 1600px; margin: 0 auto; padding: 20px; }
        
        header {
            display: flex; justify-content: space-between; align-items: center;
            padding: 20px 0; border-bottom: 1px solid #2a2a4a; margin-bottom: 20px;
        }
        h1 { font-size: 24px; color: #00d4ff; }
        
        .status { display: flex; align-items: center; gap: 10px; }
        .status-dot {
            width: 10px; height: 10px; border-radius: 50%; background: #00ff88;
            animation: pulse 2s infinite;
        }
        .status-dot.stopped { background: #ff4444; animation: none; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        
        .nav-tabs { display: flex; gap: 5px; margin-bottom: 20px; flex-wrap: wrap; }
        .nav-tab {
            padding: 10px 20px; background: #1a1a2e; border: 1px solid #2a2a4a;
            border-radius: 6px; cursor: pointer; color: #888; transition: all 0.3s;
        }
        .nav-tab:hover { background: #252540; }
        .nav-tab.active { background: #00d4ff; color: #000; border-color: #00d4ff; }
        
        .panel { display: none; }
        .panel.active { display: block; }
        
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .card {
            background: #12122a; border-radius: 12px; padding: 20px;
            border: 1px solid #2a2a4a;
        }
        .card h3 { font-size: 12px; color: #666; margin-bottom: 10px; text-transform: uppercase; }
        .card .value { font-size: 24px; font-weight: bold; }
        .card .value.positive { color: #00ff88; }
        .card .value.negative { color: #ff4444; }
        
        .chart-container { height: 350px; margin-top: 15px; }
        
        table { width: 100%; border-collapse: collapse; font-size: 13px; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #2a2a4a; }
        th { color: #666; font-weight: normal; }
        
        .signal-buy { color: #00ff88; }
        .signal-sell { color: #ff4444; }
        .signal-hold { color: #888; }
        
        .btn {
            padding: 8px 16px; border-radius: 6px; border: none;
            cursor: pointer; font-size: 13px; transition: all 0.3s;
        }
        .btn-primary { background: #00d4ff; color: #000; }
        .btn-success { background: #00ff88; color: #000; }
        .btn-danger { background: #ff4444; color: #fff; }
        .btn:hover { opacity: 0.8; }
        
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; color: #888; font-size: 12px; }
        .form-group select, .form-group input {
            width: 100%; padding: 10px; background: #1a1a2e; border: 1px solid #2a2a4a;
            border-radius: 6px; color: #e0e0e0; font-size: 14px;
        }
        
        .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 20px; }
        .stat-item { background: #12122a; padding: 15px; border-radius: 8px; }
        .stat-label { font-size: 11px; color: #666; }
        .stat-value { font-size: 18px; font-weight: bold; margin-top: 5px; }
        
        .refresh-time { font-size: 12px; color: #666; }
        
        .config-section {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;
        }
        .config-card {
            background: #12122a; padding: 20px; border-radius: 12px; border: 1px solid #2a2a4a;
        }
        .config-card h3 { margin-bottom: 15px; color: #00d4ff; }
        
        .exchange-logos { display: flex; gap: 10px; margin-bottom: 15px; }
        .exchange-logo {
            padding: 8px 16px; background: #1a1a2e; border: 1px solid #2a2a4a;
            border-radius: 6px; cursor: pointer; transition: all 0.3s;
        }
        .exchange-logo.active { background: #00d4ff; color: #000; }
        
        .strategy-list { display: flex; flex-direction: column; gap: 10px; }
        .strategy-item {
            display: flex; justify-content: space-between; align-items: center;
            padding: 15px; background: #1a1a2e; border-radius: 8px; border: 1px solid #2a2a4a;
        }
        .strategy-item.active { border-color: #00d4ff; }
        .strategy-name { font-weight: bold; }
        .strategy-status { font-size: 12px; color: #666; }
        
        .loading { text-align: center; padding: 40px; color: #666; }
        .loading:after {
            content: '...'; animation: dots 1.5s infinite;
        }
        @keyframes dots { 0% { content: '.'; } 33% { content: '..'; } 66% { content: '...'; } }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🚀 量化交易系统</h1>
            <div class="status">
                <div class="status-dot" id="statusDot"></div>
                <span id="statusText">运行中</span>
                <span class="refresh-time" id="refreshTime"></span>
            </div>
        </header>
        
        <div class="nav-tabs">
            <div class="nav-tab active" data-panel="dashboard">📊 仪表盘</div>
            <div class="nav-tab" data-panel="backtest">📈 回测</div>
            <div class="nav-tab" data-panel="positions">💰 持仓</div>
            <div class="nav-tab" data-panel="signals">📡 信号</div>
            <div class="nav-tab" data-panel="config">⚙️ 配置</div>
        </div>
        
        <!-- 仪表盘 -->
        <div class="panel active" id="dashboard">
            <div class="grid">
                <div class="card">
                    <h3>账户余额</h3>
                    <div class="value" id="balance">-</div>
                </div>
                <div class="card">
                    <h3>总盈亏</h3>
                    <div class="value" id="totalPnl">-</div>
                </div>
                <div class="card">
                    <h3>今日盈亏</h3>
                    <div class="value" id="dailyPnl">-</div>
                </div>
                <div class="card">
                    <h3>胜率</h3>
                    <div class="value" id="winRate">-</div>
                </div>
            </div>
            
            <div class="card">
                <h3>盈亏曲线</h3>
                <div class="chart-container">
                    <canvas id="pnlChart"></canvas>
                </div>
            </div>
        </div>
        
        <!-- 回测 -->
        <div class="panel" id="backtest">
            <div class="config-section">
                <div class="config-card">
                    <h3>回测参数</h3>
                    <div class="form-group">
                        <label>交易所</label>
                        <select id="btExchange">
                            <option value="binance">Binance 币安</option>
                            <option value="okex">OKX 欧易</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>交易品种</label>
                        <select id="btSymbol">
                            <option value="BTCUSDT">BTC/USDT</option>
                            <option value="ETHUSDT">ETH/USDT</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>策略</label>
                        <select id="btStrategy">
                            <option value="trend_following">趋势跟踪</option>
                            <option value="momentum">动量突破</option>
                            <option value="grid">网格交易</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>初始资金</label>
                        <input type="number" id="btInitialBalance" value="10000">
                    </div>
                    <div class="form-group">
                        <label>开始日期</label>
                        <input type="date" id="btStartDate">
                    </div>
                    <div class="form-group">
                        <label>结束日期</label>
                        <input type="date" id="btEndDate">
                    </div>
                    <button class="btn btn-primary" onclick="runBacktest()">开始回测</button>
                </div>
                
                <div class="config-card" style="flex: 1;">
                    <h3>回测结果</h3>
                    <div id="btResults">
                        <p style="color: #666;">点击"开始回测"查看结果</p>
                    </div>
                </div>
            </div>
            
            <div class="card" style="margin-top: 20px;">
                <h3>回测权益曲线</h3>
                <div class="chart-container">
                    <canvas id="btChart"></canvas>
                </div>
            </div>
        </div>
        
        <!-- 持仓 -->
        <div class="panel" id="positions">
            <div class="grid">
                <div class="card">
                    <h3>多仓</h3>
                    <div class="value positive" id="longPositions">0</div>
                </div>
                <div class="card">
                    <h3>空仓</h3>
                    <div class="value negative" id="shortPositions">0</div>
                </div>
                <div class="card">
                    <h3>持仓数量</h3>
                    <div class="value" id="totalPositions">0</div>
                </div>
                <div class="card">
                    <h3>保证金</h3>
                    <div class="value" id="totalMargin">-</div>
                </div>
            </div>
            
            <div class="card">
                <h3>当前持仓明细</h3>
                <table id="positionsTable">
                    <thead>
                        <tr><th>品种</th><th>方向</th><th>数量</th><th>开仓价</th><th>现价</th><th>盈亏</th><th>操作</th></tr>
                    </thead>
                    <tbody></tbody>
                </table>
            </div>
        </div>
        
        <!-- 信号 -->
        <div class="panel" id="signals">
            <div class="card">
                <h3>交易信号记录</h3>
                <table id="signalsTable">
                    <thead>
                        <tr><th>时间</th><th>品种</th><th>策略</th><th>信号</th><th>置信度</th><th>原因</th></tr>
                    </thead>
                    <tbody></tbody>
                </table>
            </div>
        </div>
        
        <!-- 配置 -->
        <div class="panel" id="config">
            <div class="config-section">
                <div class="config-card">
                    <h3>切换交易所</h3>
                    <div class="exchange-logos">
                        <div class="exchange-logo active" data-exchange="binance" onclick="switchExchange('binance')">Binance</div>
                        <div class="exchange-logo" data-exchange="okex" onclick="switchExchange('okex')">OKX</div>
                    </div>
                    <p style="color: #666; font-size: 12px;">当前: <span id="currentExchange">Binance</span></p>
                </div>
                
                <div class="config-card">
                    <h3>切换策略</h3>
                    <div class="strategy-list">
                        <div class="strategy-item active" data-strategy="trend_following" onclick="switchStrategy('trend_following')">
                            <div>
                                <div class="strategy-name">趋势跟踪</div>
                                <div class="strategy-status">均线交叉 + RSI + 布林带</div>
                            </div>
                            <div class="btn btn-primary" style="padding: 4px 12px; font-size: 12px;">启用</div>
                        </div>
                        <div class="strategy-item" data-strategy="momentum" onclick="switchStrategy('momentum')">
                            <div>
                                <div class="strategy-name">动量突破</div>
                                <div class="strategy-status">ATR止损 + 成交量突破</div>
                            </div>
                            <div class="btn" style="padding: 4px 12px; font-size: 12px;">启用</div>
                        </div>
                        <div class="strategy-item" data-strategy="grid" onclick="switchStrategy('grid')">
                            <div>
                                <div class="strategy-name">网格交易</div>
                                <div class="strategy-status">自动化高抛低吸</div>
                            </div>
                            <div class="btn" style="padding: 4px 12px; font-size: 12px;">启用</div>
                        </div>
                        <div class="strategy-item" data-strategy="funding" onclick="switchStrategy('funding')">
                            <div>
                                <div class="strategy-name">资金费率套利</div>
                                <div class="strategy-status">期货现货费率差</div>
                            </div>
                            <div class="btn" style="padding: 4px 12px; font-size: 12px;">启用</div>
                        </div>
                    </div>
                </div>
                
                <div class="config-card">
                    <h3>交易品种</h3>
                    <div class="form-group">
                        <label>选择交易对</label>
                        <select id="tradingSymbol" onchange="changeSymbol()">
                            <option value="BTCUSDT">BTC/USDT</option>
                            <option value="ETHUSDT">ETH/USDT</option>
                        </select>
                    </div>
                </div>
                
                <div class="config-card">
                    <h3>风险控制</h3>
                    <div class="form-group">
                        <label>最大持仓比例 (%)</label>
                        <input type="number" id="maxPosition" value="30">
                    </div>
                    <div class="form-group">
                        <label>止损比例 (%)</label>
                        <input type="number" id="stopLoss" value="2">
                    </div>
                    <div class="form-group">
                        <label>止盈比例 (%)</label>
                        <input type="number" id="takeProfit" value="4">
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let pnlChart = null;
        let btChart = null;
        
        // 设置默认日期
        document.getElementById('btEndDate').value = new Date().toISOString().split('T')[0];
        document.getElementById('btStartDate').value = new Date(Date.now() - 90*24*60*60*1000).toISOString().split('T')[0];
        
        // 标签切换
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
                tab.classList.add('active');
                document.getElementById(tab.dataset.panel).classList.add('active');
            });
        });
        
        // 初始化图表
        function initCharts() {
            const ctx = document.getElementById('pnlChart').getContext('2d');
            pnlChart = new Chart(ctx, {
                type: 'line',
                data: { labels: [], datasets: [{ label: '权益', data: [], borderColor: '#00d4ff', backgroundColor: 'rgba(0,212,255,0.1)', fill: true, tension: 0.4 }] },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: { x: { grid: { color: '#2a2a4a' }, ticks: { color: '#888' } },
                              y: { grid: { color: '#2a2a4a' }, ticks: { color: '#888' } } }
                }
            });
            
            const ctx2 = document.getElementById('btChart').getContext('2d');
            btChart = new Chart(ctx2, {
                type: 'line',
                data: { labels: [], datasets: [{ label: '权益', data: [], borderColor: '#00ff88', backgroundColor: 'rgba(0,255,136,0.1)', fill: true, tension: 0.4 }] },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: { x: { grid: { color: '#2a2a4a' }, ticks: { color: '#888' } },
                              y: { grid: { color: '#2a2a4a' }, ticks: { color: '#888' } } }
                }
            });
        }
        
        // 刷新数据
        async function refreshData() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                
                // 状态
                const statusDot = document.getElementById('statusDot');
                const statusText = document.getElementById('statusText');
                if (data.running) { statusDot.classList.remove('stopped'); statusText.textContent = '运行中'; }
                else { statusDot.classList.add('stopped'); statusText.textContent = '已停止'; }
                
                // 余额
                document.getElementById('balance').textContent = (data.portfolio?.balance || 0).toFixed(2) + ' USDT';
                
                // 总盈亏
                const totalPnl = data.portfolio?.total_pnl || 0;
                const totalPnlEl = document.getElementById('totalPnl');
                totalPnlEl.textContent = (totalPnl >= 0 ? '+' : '') + totalPnl.toFixed(2) + ' USDT';
                totalPnlEl.className = 'value ' + (totalPnl >= 0 ? 'positive' : 'negative');
                
                // 今日盈亏
                const dailyPnl = data.portfolio?.daily_pnl || 0;
                const dailyPnlEl = document.getElementById('dailyPnl');
                dailyPnlEl.textContent = (dailyPnl >= 0 ? '+' : '') + dailyPnl.toFixed(2) + ' USDT';
                dailyPnlEl.className = 'value ' + (dailyPnl >= 0 ? 'positive' : 'negative');
                
                // 胜率
                document.getElementById('winRate').textContent = ((data.portfolio?.win_rate || 0) * 100).toFixed(1) + '%';
                
                // 持仓
                const positions = data.positions || {};
                let longCount = 0, shortCount = 0;
                for (const [symbol, pos] of Object.entries(positions)) {
                    if (pos.side === 'long') longCount++;
                    else if (pos.side === 'short') shortCount++;
                }
                document.getElementById('longPositions').textContent = longCount;
                document.getElementById('shortPositions').textContent = shortCount;
                document.getElementById('totalPositions').textContent = Object.keys(positions).length;
                
                // 更新持仓表格
                const tbody = document.querySelector('#positionsTable tbody');
                tbody.innerHTML = '';
                for (const [symbol, pos] of Object.entries(positions)) {
                    const pnl = pos.unrealized_pnl || 0;
                    tbody.innerHTML += `<tr>
                        <td>${symbol}</td>
                        <td class="${pos.side === 'long' ? 'signal-buy' : 'signal-sell'}">${pos.side === 'long' ? '多' : '空'}</td>
                        <td>${pos.amount}</td>
                        <td>${pos.entry_price?.toFixed(2)}</td>
                        <td>${pos.mark_price?.toFixed(2)}</td>
                        <td class="${pnl >= 0 ? 'signal-buy' : 'signal-sell'}">${pnl >= 0 ? '+' : ''}${pnl.toFixed(2)}</td>
                        <td><button class="btn btn-danger" style="padding: 2px 8px; font-size: 11px;" onclick="closePosition('${symbol}')">平仓</button></td>
                    </tr>`;
                }
                
                // 信号
                const signalsTbody = document.querySelector('#signalsTable tbody');
                signalsTbody.innerHTML = '';
                for (const [symbol, signal] of Object.entries(data.signals || {})) {
                    const action = signal.signal?.action || 'hold';
                    signalsTbody.innerHTML += `<tr>
                        <td>${new Date(signal.timestamp).toLocaleTimeString()}</td>
                        <td>${symbol}</td>
                        <td>${signal.strategy}</td>
                        <td class="signal-${action}">${action.toUpperCase()}</td>
                        <td>${((signal.strength || 0) * 100).toFixed(0)}%</td>
                        <td>${signal.signal?.reason || '-'}</td>
                    </tr>`;
                }
                
                document.getElementById('refreshTime').textContent = new Date().toLocaleTimeString();
            } catch (e) { console.error(e); }
        }
        
        // 回测
        async function runBacktest() {
            const resultsDiv = document.getElementById('btResults');
            resultsDiv.innerHTML = '<div class="loading">正在回测中</div>';
            
            const params = {
                exchange: document.getElementById('btExchange').value,
                symbol: document.getElementById('btSymbol').value,
                strategy: document.getElementById('btStrategy').value,
                initial_balance: parseFloat(document.getElementById('btInitialBalance').value),
                start_date: document.getElementById('btStartDate').value,
                end_date: document.getElementById('btEndDate').value
            };
            
            try {
                const response = await fetch('/api/backtest', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(params)
                });
                const result = await response.json();
                
                if (result.error) {
                    resultsDiv.innerHTML = `<p style="color: #ff4444;">${result.error}</p>`;
                    return;
                }
                
                const stats = result.stats || {};
                resultsDiv.innerHTML = `
                    <div class="stats-grid">
                        <div class="stat-item"><div class="stat-label">总交易</div><div class="stat-value">${stats.total_trades || 0}</div></div>
                        <div class="stat-item"><div class="stat-label">胜率</div><div class="stat-value" style="color: ${(stats.win_rate || 0) > 0.5 ? '#00ff88' : '#ff4444'}">${((stats.win_rate || 0) * 100).toFixed(1)}%</div></div>
                        <div class="stat-item"><div class="stat-label">总盈亏</div><div class="stat-value" style="color: ${(stats.total_pnl || 0) >= 0 ? '#00ff88' : '#ff4444'}">${(stats.total_pnl || 0).toFixed(2)}</div></div>
                        <div class="stat-item"><div class="stat-label">最大回撤</div><div class="stat-value" style="color: #ff4444">${((stats.max_drawdown || 0) * 100).toFixed(1)}%</div></div>
                        <div class="stat-item"><div class="stat-label">夏普比率</div><div class="stat-value">${(stats.sharpe_ratio || 0).toFixed(2)}</div></div>
                        <div class="stat-item"><div class="stat-label">盈亏比</div><div class="stat-value">${(stats.profit_factor || 0).toFixed(2)}</div></div>
                        <div class="stat-item"><div class="stat-label">初始资金</div><div class="stat-value">${result.initial_balance}</div></div>
                        <div class="stat-item"><div class="stat-label">最终资金</div><div class="stat-value" style="color: #00d4ff">${result.final_balance?.toFixed(2)}</div></div>
                    </div>
                    <p style="color: #00d4ff; margin-top: 10px;">收益率: ${((result.total_return || 0) * 100).toFixed(2)}%</p>
                `;
                
                // 更新图表
                if (result.equity_curve) {
                    btChart.data.labels = result.equity_curve.map((e, i) => i);
                    btChart.data.datasets[0].data = result.equity_curve.map(e => e.equity);
                    btChart.update();
                }
            } catch (e) {
                resultsDiv.innerHTML = `<p style="color: #ff4444;">回测失败: ${e.message}</p>`;
            }
        }
        
        // 切换交易所
        async function switchExchange(exchange) {
            await fetch('/api/config', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ exchange })
            });
            document.querySelectorAll('.exchange-logo').forEach(el => {
                el.classList.toggle('active', el.dataset.exchange === exchange);
            });
            document.getElementById('currentExchange').textContent = exchange.toUpperCase();
        }
        
        // 切换策略
        async function switchStrategy(strategy) {
            await fetch('/api/config', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ strategy })
            });
            document.querySelectorAll('.strategy-item').forEach(el => {
                el.classList.toggle('active', el.dataset.strategy === strategy);
            });
        }
        
        // 切换交易对
        async function changeSymbol() {
            const symbol = document.getElementById('tradingSymbol').value;
            await fetch('/api/config', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ symbol })
            });
        }
        
        // 平仓
        async function closePosition(symbol) {
            await fetch('/api/close_position', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ symbol })
            });
            refreshData();
        }
        
        document.addEventListener('DOMContentLoaded', () => {
            initCharts();
            refreshData();
            setInterval(refreshData, 5000);
        });
    </script>
</body>
</html>
"""


def create_app(bot):
    """创建Flask应用"""
    app = Flask(__name__)
    
    @app.route('/')
    def index():
        return render_template_string(HTML_TEMPLATE)
    
    @app.route('/api/status')
    def status():
        bot_status = bot.get_status()
        portfolio_stats = bot.portfolio.get_stats() if bot.portfolio else {}
        
        return jsonify({
            "running": bot_status["running"],
            "balance": portfolio_stats.get("balance", 0),
            "initial_balance": portfolio_stats.get("initial_balance", 0),
            "total_pnl": portfolio_stats.get("total_pnl", 0),
            "total_pnl_pct": portfolio_stats.get("total_pnl_pct", 0),
            "daily_pnl": portfolio_stats.get("daily_pnl", 0),
            "win_rate": portfolio_stats.get("win_rate", 0),
            "positions": bot_status.get("positions", {}),
            "signals": bot_status.get("signals", {}),
            "strategies": bot_status.get("strategies", []),
            "exchange": bot.config.get("exchange", {}).get("name", "binance"),
            "current_strategy": list(bot.strategies.keys())[0] if bot.strategies else "trend_following"
        })
    
    @app.route('/api/backtest', methods=['POST'])
    async def backtest():
        data = request.json
        
        from core.backtest import run_backtest
        
        result = await run_backtest(
            symbol=data.get("symbol", "BTCUSDT"),
            strategy_name=data.get("strategy", "trend_following"),
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
            exchange_name=data.get("exchange", "binance"),
            initial_balance=data.get("initial_balance", 10000)
        )
        
        return jsonify(result)
    
    @app.route('/api/config', methods=['POST'])
    def update_config():
        data = request.json
        
        if "exchange" in data:
            bot.config["exchange"]["name"] = data["exchange"]
        if "strategy" in data:
            # 切换策略逻辑
            pass
        if "symbol" in data:
            if "symbols" not in bot.config:
                bot.config["symbols"] = []
            if data["symbol"] not in bot.config["symbols"]:
                bot.config["symbols"].append(data["symbol"])
        
        return jsonify({"status": "ok"})
    
    @app.route('/api/close_position', methods=['POST'])
    async def close_position():
        data = request.json
        symbol = data.get("symbol")
        
        if symbol in bot.positions:
            position = bot.positions[symbol]
            if position.get("side") == "long":
                await bot.exchange.close_long(symbol, position["amount"])
            elif position.get("side") == "short":
                await bot.exchange.close_short(symbol, position["amount"])
        
        return jsonify({"status": "ok"})
    
    return app
