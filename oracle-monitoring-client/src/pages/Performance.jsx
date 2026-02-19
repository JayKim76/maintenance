import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Activity, Database, Clock, Zap } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { getApiUrl } from '../utils/api';

export default function Performance() {
    const navigate = useNavigate();
    const [ashData, setAshData] = useState([]);
    const [topSql, setTopSql] = useState([]);

    useEffect(() => {
        // Fetch ASH
        fetch(`${getApiUrl()}/api/performance/ash`)
            .then(res => res.json())
            .then(data => setAshData(data))
            .catch(err => console.error("Failed to fetch ASH", err));

        // Fetch Top SQL
        fetch(`${getApiUrl()}/api/performance/top-sql`)
            .then(res => res.json())
            .then(data => setTopSql(data))
            .catch(err => console.error("Failed to fetch Top SQL", err));
    }, []);

    return (
        <div className="space-y-6 max-w-7xl mx-auto pb-10">
            <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold text-gray-100 flex items-center gap-2">
                    <Activity className="text-primary w-6 h-6" /> Performance Analysis
                </h2>
                <div className="flex gap-2">
                    <span className="px-3 py-1 bg-slate-800 rounded-md text-xs text-slate-400 border border-slate-700">Last 60 Minutes</span>
                </div>
            </div>

            {/* ASH Chart */}
            <div className="bg-surface rounded-xl border border-slate-700/50 p-6 shadow-lg">
                <div className="flex justify-between items-center mb-6">
                    <h3 className="text-lg font-semibold text-gray-100 flex items-center gap-2">
                        <Clock className="w-4 h-4 text-secondary" /> Active Session History (ASH)
                    </h3>
                </div>
                <div className="h-72 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={ashData}>
                            <defs>
                                <linearGradient id="colorAsh" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
                                    <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                            <XAxis dataKey="time" stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} dy={10} />
                            <YAxis stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} dx={-10} />
                            <Tooltip
                                contentStyle={{ backgroundColor: 'rgba(30, 41, 59, 0.95)', borderColor: '#334155', borderRadius: '8px', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.5)', color: '#f8fafc' }}
                                itemStyle={{ color: '#8b5cf6' }}
                            />
                            <Area type="monotone" dataKey="active_sessions" stroke="#8b5cf6" strokeWidth={2} fillOpacity={1} fill="url(#colorAsh)" name="Active Sessions" />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* Top SQL Table */}
            <div className="bg-surface rounded-xl border border-slate-700/50 p-6 shadow-lg overflow-hidden">
                <div className="flex justify-between items-center mb-4">
                    <h3 className="text-lg font-semibold text-gray-100 flex items-center gap-2">
                        <Database className="w-4 h-4 text-accent" /> Top SQL Statistics
                    </h3>
                </div>
                <div className="overflow-x-auto custom-scrollbar">
                    <table className="w-full text-left text-sm text-gray-300">
                        <thead className="text-xs uppercase bg-slate-800/50 text-slate-400 border-b border-slate-700">
                            <tr>
                                <th className="px-4 py-3 font-medium">SQL ID</th>
                                <th className="px-4 py-3 font-medium">SQL Text</th>
                                <th className="px-4 py-3 font-medium text-right text-warning/80">Elapsed (s)</th>
                                <th className="px-4 py-3 font-medium text-right text-primary/80">CPU (s)</th>
                                <th className="px-4 py-3 font-medium text-right">Execs</th>
                                <th className="px-4 py-3 font-medium">Module</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-700/50">
                            {topSql.map((sql, idx) => (
                                <tr key={idx} onClick={() => navigate(`/performance/sql/${sql.sql_id}`)} className="hover:bg-slate-800/30 transition-colors group cursor-pointer">
                                    <td className="px-4 py-3 font-mono text-primary text-xs group-hover:underline">{sql.sql_id}</td>
                                    <td className="px-4 py-3 max-w-[300px] truncate" title={sql.sql_text}>
                                        <span className="font-mono text-xs text-slate-400 group-hover:text-gray-200 transition-colors">{sql.sql_text}</span>
                                    </td>
                                    <td className="px-4 py-3 text-right font-bold text-gray-100 bg-slate-800/20">{sql.elapsed_time}</td>
                                    <td className="px-4 py-3 text-right">{sql.cpu_time}</td>
                                    <td className="px-4 py-3 text-right text-slate-400">{sql.executions.toLocaleString()}</td>
                                    <td className="px-4 py-3 text-slate-500 text-xs">{sql.module}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
