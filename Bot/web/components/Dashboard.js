const { useState, useEffect, useRef } = React;

const Dashboard = () => {
    // State
    const [state, setState] = useState({
        balance: 1000.0,
        peak_balance: 1000.0,
        open_positions: [],
        total_trades: 0,
        winning_trades: 0,
        realized_pnl: 0.0
    });
    const [logs, setLogs] = useState([]);
    const [scan, setScan] = useState([]);
    const [chatLog, setChatLog] = useState([
        {
            id: "welcome",
            who: "bot",
            text: "👋 Hi! I'm CryptoSentinel AI.\n\nI can now:\n• Give you live signals (\"signals on BTC\", \"analyze ETH\")\n• Trade for me intelligently (\"trade for me\", \"long the best coin\", \"short SOL 150 3x\")\n• Show real MCP data (sentiment index, L/S ratios, fear & greed)\n• Close positions, check portfolio, scan the market, backtest, reset...\n\nJust talk naturally. Example: \"give me signals on SOL\" or \"trade for me\""
        }
    ]);
    const [chatInput, setChatInput] = useState("");
    const [chatDisabled, setChatDisabled] = useState(false);
    const [refreshing, setRefreshing] = useState(false);
    const [scanning, setScanning] = useState(false);

    // Refs for Charts
    const equityChartRef = useRef(null);
    const statsChartRef = useRef(null);
    const equityChartInst = useRef(null);
    const statsChartInst = useRef(null);
    const chatLogEndRef = useRef(null);

    // Helper formatting
    const formatCurrency = (val) => {
        return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val);
    };

    const formatPercent = (val) => {
        const formatted = val.toFixed(2);
        return val >= 0 ? `+${formatted}%` : `${formatted}%`;
    };

    // Fetch API data
    const fetchStateAndLogs = async () => {
        try {
            const [stateRes, logsRes, scanRes] = await Promise.all([
                fetch('/api/state'),
                fetch('/api/logs'),
                fetch('/api/scan')
            ]);
            
            const stateData = await stateRes.json();
            const logsData = await logsRes.json();
            const scanData = await scanRes.json();

            setState(stateData);
            setLogs(logsData);
            setScan(scanData);
        } catch (err) {
            console.error("Error fetching dashboard data:", err);
        }
    };

    // Trigger full manual refresh
    const handleManualRefresh = () => {
        setRefreshing(true);
        fetchStateAndLogs().finally(() => {
            setTimeout(() => setRefreshing(false), 600);
        });
    };

    // Trigger manual scan refresh
    const handleScanRefresh = () => {
        setScanning(true);
        fetch('/api/nl', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command: 'scan the market' })
        }).then(() => {
            setTimeout(() => {
                fetchStateAndLogs();
                setScanning(false);
            }, 2000);
        }).catch(() => {
            setScanning(false);
        });
    };

    // Send AI Command
    const sendNLCommand = async (customCmd) => {
        const text = (customCmd || chatInput).trim();
        if (!text) return;

        if (!customCmd) {
            setChatInput("");
        }

        // Add user message
        const userMsgId = "user-" + Date.now();
        setChatLog(prev => [...prev, { id: userMsgId, who: "user", text }]);
        
        setChatDisabled(true);

        // Add thinking
        const thinkingId = "thinking-" + Date.now();
        setChatLog(prev => [...prev, { id: thinkingId, who: "bot", text: "⏳ Thinking...", isThinking: true }]);

        try {
            const resp = await fetch('/api/nl', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: text })
            });
            const data = await resp.json();

            // Remove thinking bubble and add response
            setChatLog(prev => {
                const filtered = prev.filter(m => m.id !== thinkingId);
                const reply = data.message || (data.ok ? "Done." : "Something went wrong.");
                return [...filtered, { id: "bot-" + Date.now(), who: "bot", text: reply }];
            });

            // Action triggers refresh
            if (data.action && ['scan_trade', 'scan_only', 'reset', 'backtest', 'refresh', 'trade', 'close'].includes(data.action)) {
                setTimeout(() => {
                    fetchStateAndLogs();
                    setChatLog(prev => [...prev, { id: "refresh-" + Date.now(), who: "bot", text: "✅ Dashboard panels refreshed with latest data.", isSmall: true }]);
                }, 650);
            }

            if (data.scan_preview && data.scan_preview.length) {
                const preview = data.scan_preview.slice(0, 3).map(s => `${s.symbol} ${s.aggregate_score >= 0 ? '+' : ''}${s.aggregate_score} → ${s.decision}`).join(' • ');
                setChatLog(prev => [...prev, { id: "preview-" + Date.now(), who: "bot", text: "Top from scan: " + preview, isSmall: true }]);
            }

        } catch (e) {
            setChatLog(prev => {
                const filtered = prev.filter(m => m.id !== thinkingId);
                return [...filtered, { id: "err-" + Date.now(), who: "bot", text: "❌ Network or server error. Is the server running?" }];
            });
            console.error(e);
        } finally {
            setChatDisabled(false);
        }
    };

    // Chat auto-scroll
    useEffect(() => {
        if (chatLogEndRef.current) {
            chatLogEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [chatLog]);

    // Initial load + Polling
    useEffect(() => {
        fetchStateAndLogs();
        const interval = setInterval(fetchStateAndLogs, 5000);
        return () => clearInterval(interval);
    }, []);

    // Render/Update Chart.js charts
    useEffect(() => {
        if (!logs || !state) return;
        const closedTrades = logs.filter(t => t.status === 'CLOSED');

        // 1. Calculate Equity Curve
        let currentEquity = 1000.00;
        const equityData = [1000.00];
        const labels = ['Start'];
        const chronologicalTrades = [...closedTrades].reverse();

        chronologicalTrades.forEach((trade, idx) => {
            const pnl = parseFloat(trade.pnl_usdt || 0);
            currentEquity += pnl;
            equityData.push(currentEquity);
            const date = new Date(trade.timestamp);
            const label = isNaN(date.getTime()) ? `Trade ${idx+1}` : `${date.getMonth()+1}/${date.getDate()} ${date.getHours()}:00`;
            labels.push(label);
        });

        // Setup Equity Chart
        if (equityChartRef.current) {
            const ctx = equityChartRef.current.getContext('2d');
            if (equityChartInst.current) {
                equityChartInst.current.destroy();
            }

            const gradient = ctx.createLinearGradient(0, 0, 0, 300);
            gradient.addColorStop(0, 'rgba(139, 92, 246, 0.4)');
            gradient.addColorStop(1, 'rgba(139, 92, 246, 0.0)');

            equityChartInst.current = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Portfolio Value (USDT)',
                        data: equityData,
                        borderColor: '#8b5cf6',
                        borderWidth: 2,
                        backgroundColor: gradient,
                        fill: true,
                        tension: 0.3,
                        pointRadius: labels.length === 1 ? 0 : 3,
                        pointHoverRadius: 5,
                        pointHitRadius: 10,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: {
                            grid: { display: false },
                            ticks: { color: '#8b86a3', font: { size: 10 } }
                        },
                        y: {
                            grid: { color: 'rgba(255, 255, 255, 0.04)' },
                            ticks: { color: '#8b86a3', font: { size: 10 } }
                        }
                    }
                }
            });
        }

        // Setup Stats Chart
        const wins = state.winning_trades;
        const losses = Math.max(0, state.total_trades - state.winning_trades);

        if (statsChartRef.current) {
            const ctxStats = statsChartRef.current.getContext('2d');
            if (statsChartInst.current) {
                statsChartInst.current.destroy();
            }

            statsChartInst.current = new Chart(ctxStats, {
                type: 'doughnut',
                data: {
                    labels: ['Winning Trades', 'Losing Trades'],
                    datasets: [{
                        data: [wins, losses],
                        backgroundColor: ['#10b981', '#ef4444'],
                        borderColor: '#06040a',
                        borderWidth: 2,
                        hoverOffset: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                color: '#f3f0f7',
                                font: { family: 'Barlow', size: 12 },
                                padding: 15
                            }
                        }
                    },
                    cutout: '70%'
                }
            });
        }

        return () => {
            if (equityChartInst.current) equityChartInst.current.destroy();
            if (statsChartInst.current) statsChartInst.current.destroy();
        };
    }, [logs, state]);

    // Derived stats
    const totalValuation = state.balance + state.open_positions.reduce((acc, p) => acc + p.amount_usdt, 0);
    const winRate = state.total_trades > 0 ? (state.winning_trades / state.total_trades) * 100 : 0.0;
    const closedTrades = logs.filter(t => t.status === 'CLOSED');
    const displayTrades = [...closedTrades].reverse().slice(0, 8);

    // Sorted Scan
    const sortedScan = [...scan]
        .sort((a, b) => Math.abs(b.aggregate_score) - Math.abs(a.aggregate_score))
        .slice(0, 10);

    return (
        <div className="relative w-full min-h-screen bg-black text-white pt-24 pb-12 px-4 md:px-8 lg:px-16 z-10 flex flex-col justify-between overflow-x-hidden">
            {/* Background looping FadingVideo */}
            <window.FadingVideo 
                src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260418_094631_d30ab262-45ee-4b7d-99f3-5d5848c8ef13.mp4"
                className="absolute inset-0 w-full h-full object-cover z-0 opacity-20 pointer-events-none"
            />

            <div className="relative z-10 max-w-[1400px] w-full mx-auto flex flex-col gap-6">
                
                {/* Header title */}
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-2">
                    <div>
                        <h2 className="font-heading italic text-5xl md:text-6xl text-white leading-none tracking-tight">
                            Neural Dashboard
                        </h2>
                        <p className="font-body text-white/60 text-sm mt-1">Autonomous Trader Perception, Decision and Execution State.</p>
                    </div>
                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-2 p-1 px-3 rounded-full bg-white/5 border border-white/10 text-xs">
                            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                            <span className="text-white/80 font-medium">Paper Sim Active</span>
                        </div>
                    </div>
                </div>

                {/* KPI Metrics row */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    {/* Capital */}
                    <div className="liquid-glass rounded-2xl p-5 flex items-center gap-4">
                        <div className="w-12 h-12 rounded-xl bg-white/5 flex items-center justify-center text-violet-400 text-xl border border-white/10">
                            <i className="fa-solid fa-wallet"></i>
                        </div>
                        <div>
                            <span className="text-white/60 text-xs font-body uppercase tracking-wider block">Sim Capital</span>
                            <span className="font-heading italic text-3xl text-white font-bold leading-none block mt-1">
                                {formatCurrency(totalValuation)} <span className="text-xs text-white/40 not-italic font-normal">USDT</span>
                            </span>
                        </div>
                    </div>
                    
                    {/* Realized PnL */}
                    <div className="liquid-glass rounded-2xl p-5 flex items-center gap-4">
                        <div className="w-12 h-12 rounded-xl bg-white/5 flex items-center justify-center text-violet-400 text-xl border border-white/10">
                            <i className="fa-solid fa-chart-line"></i>
                        </div>
                        <div>
                            <span className="text-white/60 text-xs font-body uppercase tracking-wider block">Realized PnL</span>
                            <span className={`font-heading italic text-3xl font-bold leading-none block mt-1 ${state.realized_pnl >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                                {state.realized_pnl >= 0 ? "+" : ""}{formatCurrency(state.realized_pnl)}
                            </span>
                        </div>
                    </div>

                    {/* Peak Balance */}
                    <div className="liquid-glass rounded-2xl p-5 flex items-center gap-4">
                        <div className="w-12 h-12 rounded-xl bg-white/5 flex items-center justify-center text-violet-400 text-xl border border-white/10">
                            <i className="fa-solid fa-mountain-sun"></i>
                        </div>
                        <div>
                            <span className="text-white/60 text-xs font-body uppercase tracking-wider block">Peak Balance</span>
                            <span className="font-heading italic text-3xl text-white font-bold leading-none block mt-1">
                                {formatCurrency(state.peak_balance)}
                            </span>
                        </div>
                    </div>

                    {/* Win Rate */}
                    <div className="liquid-glass rounded-2xl p-5 flex items-center gap-4">
                        <div className="w-12 h-12 rounded-xl bg-white/5 flex items-center justify-center text-violet-400 text-xl border border-white/10">
                            <i className="fa-solid fa-percent"></i>
                        </div>
                        <div>
                            <span className="text-white/60 text-xs font-body uppercase tracking-wider block">Win Rate</span>
                            <span className={`font-heading italic text-3xl font-bold leading-none block mt-1 ${winRate >= 50 ? "text-emerald-400" : (state.total_trades > 0 ? "text-red-400" : "text-white")}`}>
                                {winRate.toFixed(1)}%
                            </span>
                        </div>
                    </div>
                </div>

                {/* Charts Row */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Equity curve */}
                    <div className="liquid-glass rounded-2xl p-6 lg:col-span-2 flex flex-col justify-between">
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="font-heading italic text-2xl text-white">Equity Performance</h3>
                            <span className="text-xs px-2.5 py-1 rounded-full bg-white/5 border border-white/10 text-white/60">Portfolio Curve</span>
                        </div>
                        <div className="h-[280px] w-full relative">
                            <canvas ref={equityChartRef}></canvas>
                        </div>
                    </div>

                    {/* Win rate doughnut */}
                    <div className="liquid-glass rounded-2xl p-6 flex flex-col justify-between">
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="font-heading italic text-2xl text-white">Trade Distribution</h3>
                        </div>
                        <div className="h-[280px] w-full relative flex items-center justify-center">
                            <canvas ref={statsChartRef}></canvas>
                        </div>
                    </div>
                </div>

                {/* Positions & Executed Trades Tables */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Active Positions */}
                    <div className="liquid-glass rounded-2xl p-6 flex flex-col justify-between">
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="font-heading italic text-2xl text-white">Active Positions</h3>
                            <span className="text-xs px-2.5 py-0.5 rounded-full bg-violet-500/10 text-violet-400 border border-violet-500/20">
                                {state.open_positions.length} Active
                            </span>
                        </div>
                        <div className="overflow-x-auto w-full min-h-[220px] max-h-[260px]">
                            <table className="w-full text-left text-sm border-collapse">
                                <thead>
                                    <tr className="border-b border-white/10 text-white/50 text-[11px] uppercase tracking-wider">
                                        <th className="py-2.5 font-normal">Asset</th>
                                        <th className="py-2.5 font-normal">Direction</th>
                                        <th className="py-2.5 font-normal">Size</th>
                                        <th className="py-2.5 font-normal">Entry</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {state.open_positions.length === 0 ? (
                                        <tr>
                                            <td colSpan="4" className="text-center py-12 text-white/30 font-body text-xs">
                                                No active open positions
                                            </td>
                                        </tr>
                                    ) : (
                                        state.open_positions.map((pos, i) => (
                                            <tr key={i} className="border-b border-white/5 text-xs hover:bg-white/[0.02] transition-colors">
                                                <td className="py-3 font-semibold text-white">{pos.asset}</td>
                                                <td className="py-3">
                                                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${pos.action.includes('LONG') ? "bg-emerald-400/10 text-emerald-400" : "bg-red-400/10 text-red-400"}`}>
                                                        {pos.action}
                                                    </span>
                                                </td>
                                                <td className="py-3 font-mono">{formatCurrency(pos.amount_usdt)}</td>
                                                <td className="py-3 font-mono">{formatCurrency(pos.entry_price)}</td>
                                            </tr>
                                        ))
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    {/* Executed Trades */}
                    <div className="liquid-glass rounded-2xl p-6 lg:col-span-2 flex flex-col justify-between">
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="font-heading italic text-2xl text-white">Recent Trade Logs</h3>
                            <button 
                                onClick={handleManualRefresh}
                                className="px-3 py-1 bg-white/5 border border-white/10 hover:bg-white/10 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all"
                            >
                                <i className={`fa-solid fa-rotate ${refreshing ? "fa-spin" : ""}`}></i>
                                <span>{refreshing ? "Updating..." : "Refresh"}</span>
                            </button>
                        </div>
                        <div className="overflow-x-auto w-full min-h-[220px] max-h-[260px]">
                            <table className="w-full text-left text-sm border-collapse">
                                <thead>
                                    <tr className="border-b border-white/10 text-white/50 text-[11px] uppercase tracking-wider">
                                        <th className="py-2.5 font-normal">Timestamp</th>
                                        <th className="py-2.5 font-normal">Asset</th>
                                        <th className="py-2.5 font-normal">Action</th>
                                        <th className="py-2.5 font-normal">Size</th>
                                        <th className="py-2.5 font-normal">Entry</th>
                                        <th className="py-2.5 font-normal">Exit</th>
                                        <th className="py-2.5 font-normal">PnL ($)</th>
                                        <th className="py-2.5 font-normal">PnL (%)</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {displayTrades.length === 0 ? (
                                        <tr>
                                            <td colSpan="8" className="text-center py-12 text-white/30 font-body text-xs">
                                                No trading records found. Execute trades using command console below.
                                            </td>
                                        </tr>
                                    ) : (
                                        displayTrades.map((trade, i) => {
                                            const pnlUsdt = parseFloat(trade.pnl_usdt || 0);
                                            const pnlPct = parseFloat(trade.pnl_pct || 0);
                                            const isWin = pnlUsdt >= 0;
                                            return (
                                                <tr key={i} className="border-b border-white/5 text-xs hover:bg-white/[0.02] transition-colors">
                                                    <td className="py-3 text-white/40 font-mono text-[10px]">{trade.timestamp}</td>
                                                    <td className="py-3 font-semibold text-white">{trade.asset}</td>
                                                    <td className="py-3">
                                                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${trade.action.toLowerCase().includes('buy') || trade.action.toLowerCase().includes('long') ? "bg-emerald-400/10 text-emerald-400" : "bg-red-400/10 text-red-400"}`}>
                                                            {trade.action}
                                                        </span>
                                                    </td>
                                                    <td className="py-3 font-mono">{formatCurrency(parseFloat(trade.amount_usdt))}</td>
                                                    <td className="py-3 font-mono">{formatCurrency(parseFloat(trade.entry_price))}</td>
                                                    <td className="py-3 font-mono">{formatCurrency(parseFloat(trade.exit_price))}</td>
                                                    <td className="py-3 font-mono">
                                                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${isWin ? "bg-emerald-400/10 text-emerald-400" : "bg-red-400/10 text-red-400"}`}>
                                                            {isWin ? "+" : ""}{formatCurrency(pnlUsdt)}
                                                        </span>
                                                    </td>
                                                    <td className={`py-3 font-mono ${isWin ? "text-emerald-400" : "text-red-400"}`}>
                                                        {formatPercent(pnlPct)}
                                                    </td>
                                                </tr>
                                            );
                                        })
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                {/* Market Scanner Panel */}
                <div className="liquid-glass rounded-2xl p-6">
                    <div className="flex justify-between items-center mb-4 border-b border-white/10 pb-3">
                        <div className="flex items-center gap-2">
                            <i className="fa-solid fa-satellite-dish text-violet-400 text-xl"></i>
                            <h3 className="font-heading italic text-2xl text-white">Market Scanner — Top Conviction Cryptocurrencies</h3>
                        </div>
                        <button 
                            onClick={handleScanRefresh}
                            className="px-3 py-1 bg-white/5 border border-white/10 hover:bg-white/10 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all"
                        >
                            <i className={`fa-solid fa-radar ${scanning ? "fa-spin" : ""}`}></i>
                            <span>{scanning ? "Scanning Live..." : "Refresh Scan"}</span>
                        </button>
                    </div>
                    <div className="overflow-x-auto w-full max-h-[300px]">
                        <table className="w-full text-left text-sm border-collapse">
                            <thead>
                                <tr className="border-b border-white/10 text-white/50 text-[11px] uppercase tracking-wider">
                                    <th className="py-2.5 font-normal">Rank</th>
                                    <th className="py-2.5 font-normal">Symbol</th>
                                    <th className="py-2.5 font-normal">Price</th>
                                    <th className="py-2.5 font-normal">24h Change</th>
                                    <th className="py-2.5 font-normal">Volume (USDT)</th>
                                    <th className="py-2.5 font-normal">Score</th>
                                    <th className="py-2.5 font-normal">Decision</th>
                                </tr>
                            </thead>
                            <tbody>
                                {sortedScan.length === 0 ? (
                                    <tr>
                                        <td colSpan="7" className="text-center py-12 text-white/30 font-body text-xs">
                                            No scan records found. Run scan from console or click Refresh Scan above.
                                        </td>
                                    </tr>
                                ) : (
                                    sortedScan.map((coin, idx) => {
                                        const scoreVal = coin.aggregate_score || 0;
                                        const changeVal = coin.change_24h_pct || 0;
                                        const volStr = coin.volume_24h >= 1e9 ? `$${(coin.volume_24h / 1e9).toFixed(1)}B` : `$${(coin.volume_24h / 1e6).toFixed(1)}M`;
                                        const scoreClass = scoreVal > 1.5 ? 'text-emerald-400' : (scoreVal < -1.5 ? 'text-red-400' : 'text-white/60');
                                        const decClass = coin.decision.includes('BUY') ? 'bg-emerald-400/10 text-emerald-400 border border-emerald-400/20' : (coin.decision.includes('SELL') ? 'bg-red-400/10 text-red-400 border border-red-400/20' : 'bg-white/5 text-white/60 border border-white/10');
                                        return (
                                            <tr key={idx} className="border-b border-white/5 text-xs hover:bg-white/[0.02] transition-colors">
                                                <td className="py-3 font-semibold text-white/40">#{idx + 1}</td>
                                                <td className="py-3 font-bold text-white">{coin.symbol}</td>
                                                <td className="py-3 font-mono">{formatCurrency(coin.price)}</td>
                                                <td className={`py-3 font-mono ${changeVal >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                                                    {changeVal >= 0 ? "+" : ""}{changeVal.toFixed(2)}%
                                                </td>
                                                <td className="py-3 font-mono text-white/70">{volStr}</td>
                                                <td className={`py-3 font-mono font-bold ${scoreClass}`}>
                                                    {scoreVal >= 0 ? "+" : ""}{scoreVal.toFixed(2)}
                                                </td>
                                                <td className="py-3">
                                                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${decClass}`}>
                                                        {coin.decision}
                                                    </span>
                                                </td>
                                            </tr>
                                        );
                                    })
                                )}
                            </tbody>
                        </table>
                    </div>
                    <div className="mt-3 pt-3 border-t border-white/5 text-white/40 text-xs">
                        Scans top-volume USDT pairs on Bitget. Excludes tokenized stock assets (R-prefix) and leveraged tokens. Technicals heavily weighted with fear, greed, macro, RSS news sentiment, and on-chain intelligence.
                    </div>
                </div>

                {/* AI Command Center */}
                <div className="liquid-glass rounded-2xl p-6 flex flex-col gap-4">
                    <div className="flex justify-between items-center border-b border-white/10 pb-3">
                        <div className="flex items-center gap-2">
                            <i className="fa-solid fa-robot text-violet-400 text-xl"></i>
                            <h3 className="font-heading italic text-2xl text-white">Command the AI Agent</h3>
                        </div>
                        <span className="text-[10px] font-mono tracking-widest px-2.5 py-0.5 rounded-full bg-violet-500/10 text-violet-400 border border-violet-500/20 uppercase">
                            Natural Language Interface
                        </span>
                    </div>

                    <div className="text-xs text-white/60 leading-relaxed font-body">
                        Instruct the trading agent using plain English commands. Start strategy scans, trigger autonomous multi-coin trades, execute custom futures orders, audit portfolio logs, or reset state logs on the fly.
                    </div>

                    {/* Chat log window */}
                    <div className="bg-black/40 border border-white/5 rounded-xl p-4 h-[240px] overflow-y-auto flex flex-col gap-3 font-body text-xs">
                        {chatLog.map((msg) => (
                            <div 
                                key={msg.id} 
                                className={`max-w-[85%] p-3 rounded-xl border flex flex-col gap-1 ${
                                    msg.who === 'user' 
                                        ? 'self-end bg-violet-500/10 border-violet-500/30 text-white/90' 
                                        : 'self-start bg-white/5 border-white/10 text-white/90'
                                } ${msg.isSmall ? 'opacity-70 text-[10px]' : ''}`}
                            >
                                <div className={`flex items-center gap-1.5 text-[9px] text-white/40 font-semibold ${msg.who === 'user' ? 'justify-end' : ''}`}>
                                    <i className={msg.who === 'user' ? "fa-solid fa-user" : "fa-solid fa-robot"}></i>
                                    <span>{msg.who === 'user' ? 'You' : 'Agent'}</span>
                                </div>
                                <div className="whitespace-pre-wrap leading-normal font-light">
                                    {msg.text}
                                </div>
                            </div>
                        ))}
                        <div ref={chatLogEndRef} />
                    </div>

                    {/* Input Row */}
                    <div className="flex gap-2 items-center">
                        <input 
                            type="text"
                            value={chatInput}
                            disabled={chatDisabled}
                            onChange={(e) => setChatInput(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' && !chatDisabled) {
                                    e.preventDefault();
                                    sendNLCommand();
                                }
                            }}
                            placeholder='e.g. "analyze the market and take trade where it is most profitable with 3x leverage"'
                            className="flex-1 bg-black/50 border border-white/10 text-white text-xs rounded-full px-5 py-3 outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20 transition-all font-body"
                        />
                        <button 
                            disabled={chatDisabled || !chatInput.trim()}
                            onClick={() => sendNLCommand()}
                            className="h-10 px-5 bg-white text-black hover:bg-neutral-100 disabled:opacity-40 disabled:hover:bg-white rounded-full flex items-center justify-center gap-1.5 transition-all text-xs font-semibold"
                        >
                            <i className="fa-solid fa-paper-plane"></i>
                            <span>Send</span>
                        </button>
                    </div>

                    {/* Quick Command Pills */}
                    <div className="flex flex-wrap gap-2 mt-1">
                        <button 
                            disabled={chatDisabled}
                            onClick={() => sendNLCommand("give me signals on BTC")}
                            className="px-3 py-1.5 rounded-full bg-white/5 border border-white/10 hover:bg-white/10 disabled:opacity-50 text-white/80 hover:text-white transition-all text-[11px]"
                        >
                            Signals for BTC
                        </button>
                        <button 
                            disabled={chatDisabled}
                            onClick={() => sendNLCommand("trade for me with 3x leverage")}
                            className="px-3 py-1.5 rounded-full bg-white/5 border border-white/10 hover:bg-white/10 disabled:opacity-50 text-white/80 hover:text-white transition-all text-[11px]"
                        >
                            Trade for me (autonomous)
                        </button>
                        <button 
                            disabled={chatDisabled}
                            onClick={() => sendNLCommand("what is the market sentiment")}
                            className="px-3 py-1.5 rounded-full bg-white/5 border border-white/10 hover:bg-white/10 disabled:opacity-50 text-white/80 hover:text-white transition-all text-[11px]"
                        >
                            Market sentiment + L/S
                        </button>
                        <button 
                            disabled={chatDisabled}
                            onClick={() => sendNLCommand("analyze ETH")}
                            className="px-3 py-1.5 rounded-full bg-white/5 border border-white/10 hover:bg-white/10 disabled:opacity-50 text-white/80 hover:text-white transition-all text-[11px]"
                        >
                            Analyze ETH
                        </button>
                        <button 
                            disabled={chatDisabled}
                            onClick={() => sendNLCommand("close my positions")}
                            className="px-3 py-1.5 rounded-full bg-white/5 border border-white/10 hover:bg-white/10 disabled:opacity-50 text-white/80 hover:text-white transition-all text-[11px]"
                        >
                            Close everything
                        </button>
                        <button 
                            disabled={chatDisabled}
                            onClick={() => sendNLCommand("show my portfolio")}
                            className="px-3 py-1.5 rounded-full bg-white/5 border border-white/10 hover:bg-white/10 disabled:opacity-50 text-white/80 hover:text-white transition-all text-[11px]"
                        >
                            Portfolio status
                        </button>
                        <button 
                            disabled={chatDisabled}
                            onClick={() => sendNLCommand("scan the market")}
                            className="px-3 py-1.5 rounded-full bg-white/5 border border-white/10 hover:bg-white/10 disabled:opacity-50 text-white/80 hover:text-white transition-all text-[11px]"
                        >
                            Just scan coins
                        </button>
                        <button 
                            disabled={chatDisabled}
                            onClick={() => sendNLCommand("reset the portfolio")}
                            className="px-3 py-1.5 rounded-full bg-white/5 border border-white/10 hover:bg-white/10 disabled:opacity-50 text-white/80 hover:text-white transition-all text-[11px]"
                        >
                            Reset portfolio
                        </button>
                    </div>
                </div>

                {/* Footer */}
                <div className="text-center text-[11px] text-white/30 mt-6 pt-4 border-t border-white/10 font-body">
                    &copy; 2026 CryptoSentinel AI Trading Framework. Built for the Bitget AI Base Camp Hackathon.
                </div>
            </div>
        </div>
    );
};

window.Dashboard = Dashboard;
