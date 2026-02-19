import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area, Cell, PieChart, Pie } from 'recharts';
import { Cpu, Database, Users, HardDrive, ArrowUpRight, ArrowDownRight, Server, Activity } from 'lucide-react';

import { getWsUrl } from '../utils/api';

export default function Dashboard() {
    const [metrics, setMetrics] = useState(null);
    const [history, setHistory] = useState([]);
    const [connected, setConnected] = useState(false);

    useEffect(() => {
        const ws = new WebSocket(`${getWsUrl()}/api/dashboard/ws`);

        ws.onopen = () => {
            console.log('Connected to backend');
            setConnected(true);
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            setMetrics(data);

            setHistory(prev => {
                const newPoint = {
                    time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
                    value: data.cpu_load
                };
                const newHistory = [...prev, newPoint];
                return newHistory.slice(-20); // Keep last 20 points
            });
        };

        ws.onclose = () => setConnected(false);

        return () => ws.close();
    }, []);

    if (!metrics) return (
        <div className="flex h-full items-center justify-center text-slate-500">
            <div className="flex flex-col items-center gap-2">
                <Activity className="animate-spin w-8 h-8" />
                <span>Connecting to Oracle Engine...</span>
            </div>
        </div>
    );

    return (
        <div className="space-y-6 max-w-7xl mx-auto">
            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <StatCard
                    title="CPU Load"
                    value={`${metrics.cpu_load}%`}
                    trend={metrics.cpu_load > 80 ? 'High' : 'Normal'}
                    trendUp={metrics.cpu_load > 80}
                    icon={<Cpu size={24} className="text-primary" />}
                    color="primary"
                />
                <StatCard
                    title="Memory Usage"
                    value={`${metrics.memory_usage}%`}
                    sub="Physical RAM"
                    icon={<Database size={24} className="text-accent" />}
                    color="accent"
                />
                <StatCard
                    title="Active Sessions"
                    value={metrics.active_sessions}
                    sub="Connected Users"
                    trend="-2%"
                    icon={<Users size={24} className="text-secondary" />}
                    color="secondary"
                />
                <StatCard
                    title="Disk I/O"
                    value={`${metrics.disk_io} MB/s`}
                    sub="Read/Write"
                    icon={<HardDrive size={24} className="text-blue-500" />}
                    color="blue-500"
                />
            </div>

            {/* Main Charts Area */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Main Graph */}
                <div className="lg:col-span-2 bg-surface rounded-xl border border-slate-700/50 p-6 flex flex-col shadow-lg shadow-black/20 relative overflow-hidden group">
                    <div className="absolute top-0 right-0 p-4 opacity-50"><Activity className="text-slate-700 w-24 h-24 -mr-8 -mt-8" /></div>
                    <div className="flex justify-between items-center mb-6 relative z-10">
                        <div>
                            <h3 className="text-lg font-semibold text-gray-100 flex items-center gap-2">
                                <Server className="w-4 h-4 text-primary" /> Live CPU Load
                            </h3>
                            <p className="text-xs text-slate-400 mt-1">Real-time WebSocket Stream {connected ? '(Online)' : '(Offline)'}</p>
                        </div>
                        <div className={`w-2 h-2 rounded-full ${connected ? 'bg-secondary animate-pulse' : 'bg-danger'}`}></div>
                    </div>

                    <div className="flex-1 w-full min-h-[300px] relative z-10">
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={history}>
                                <defs>
                                    <linearGradient id="colorCpu" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.3} />
                                        <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} strokeOpacity={0.5} />
                                <XAxis dataKey="time" stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} dy={10} />
                                <YAxis domain={[0, 100]} stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} dx={-10} />
                                <Tooltip
                                    contentStyle={{ backgroundColor: 'rgba(30, 41, 59, 0.9)', borderColor: '#334155', borderRadius: '8px', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.5)', color: '#f8fafc' }}
                                    itemStyle={{ color: '#06b6d4' }}
                                />
                                <Area type="monotone" dataKey="value" stroke="#06b6d4" strokeWidth={2} fillOpacity={1} fill="url(#colorCpu)" animationDuration={300} isAnimationActive={true} />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Wait Events Distribution */}
                <div className="bg-surface rounded-xl border border-slate-700/50 p-6 shadow-lg shadow-black/20 flex flex-col">
                    <h3 className="text-lg font-semibold mb-6 text-gray-100">Wait Events</h3>

                    <div className="flex-1 flex items-center justify-center relative">
                        <ResponsiveContainer width="100%" height={200}>
                            <PieChart>
                                <Pie
                                    data={metrics.wait_events || []}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={60}
                                    outerRadius={80}
                                    paddingAngle={5}
                                    dataKey="value"
                                    stroke="none"
                                >
                                    {(metrics.wait_events || []).map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={entry.color} />
                                    ))}
                                </Pie>
                                <Tooltip contentStyle={{ backgroundColor: '#1e293b', borderRadius: '8px', border: 'none' }} />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>

                    <div className="mt-6 space-y-3">
                        {(metrics.wait_events || []).slice(0, 3).map((item, idx) => (
                            <div key={idx} className="flex items-center justify-between text-sm">
                                <div className="flex items-center gap-2">
                                    <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: item.color }}></span>
                                    <span className="text-slate-300">{item.name}</span>
                                </div>
                                <span className="font-mono text-slate-400">{item.value}%</span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Top SQL from Backend? Not yet in Dashboard.jsx, keeping Alerts placeholder */}
            <div className="bg-surface rounded-xl border border-slate-700/50 p-6 shadow-lg shadow-black/20">
                <h3 className="text-lg font-semibold text-gray-100 mb-4">Mock Critical Alerts</h3>
                <div className="text-slate-400 text-sm">Alerts integration pending...</div>
            </div>
        </div>
    );
}

function StatCard({ title, value, sub, trend, trendUp, icon, color }) {
    const colorMap = {
        primary: 'text-primary bg-primary/10 border-primary/20',
        secondary: 'text-secondary bg-secondary/10 border-secondary/20',
        accent: 'text-accent bg-accent/10 border-accent/20',
        'blue-500': 'text-blue-500 bg-blue-500/10 border-blue-500/20',
    };

    return (
        <div className="bg-surface rounded-xl border border-slate-700/50 p-5 hover:border-slate-600 transition-all duration-300 group hover:shadow-lg hover:shadow-primary/5 hover:-translate-y-1">
            <div className="flex justify-between items-start mb-4">
                <div className={`p-2.5 rounded-lg transition-colors ${colorMap[color].replace('border-', '')} group-hover:bg-opacity-20`}>{icon}</div>
                {trend && (
                    <div className={`flex items-center text-xs font-medium px-1.5 py-0.5 rounded ${trendUp ? 'text-danger bg-danger/10' : 'text-secondary bg-secondary/10'}`}>
                        {trendUp ? <ArrowUpRight size={12} className="mr-1" /> : <ArrowDownRight size={12} className="mr-1" />}
                        {trend}
                    </div>
                )}
            </div>
            <div className="text-3xl font-bold text-gray-100 mb-1 tracking-tight">{value}</div>
            <div className="text-xs text-slate-400 font-medium">{sub || title}</div>
        </div>
    );
}
