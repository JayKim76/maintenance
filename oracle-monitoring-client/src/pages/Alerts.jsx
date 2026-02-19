import { useState, useEffect } from 'react';
import { Bell, AlertTriangle, Info, CheckCircle, Filter } from 'lucide-react';
import { getApiUrl } from '../utils/api';

export default function Alerts() {
    const [alerts, setAlerts] = useState([]);
    const [filter, setFilter] = useState('ALL'); // ALL, CRITICAL, WARNING

    useEffect(() => {
        fetch(`${getApiUrl()}/api/alerts/history`)
            .then(res => res.json())
            .then(data => setAlerts(data))
            .catch(err => console.error("Failed to fetch alerts", err));
    }, []);

    const filteredAlerts = filter === 'ALL'
        ? alerts
        : alerts.filter(a => a.severity === filter);

    const getIcon = (severity) => {
        switch (severity) {
            case 'CRITICAL': return <AlertTriangle className="text-danger" />;
            case 'WARNING': return <Info className="text-warning" />;
            default: return <CheckCircle className="text-primary" />;
        }
    };

    const getBadgeStyle = (severity) => {
        switch (severity) {
            case 'CRITICAL': return 'bg-danger/10 text-danger border-danger/20';
            case 'WARNING': return 'bg-warning/10 text-warning border-warning/20';
            default: return 'bg-primary/10 text-primary border-primary/20';
        }
    };

    return (
        <div className="space-y-6 max-w-5xl mx-auto">
            <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold text-gray-100 flex items-center gap-2">
                    <Bell className="text-primary" /> Incident History
                </h2>
                <div className="flex gap-2">
                    {['ALL', 'CRITICAL', 'WARNING'].map(f => (
                        <button
                            key={f}
                            onClick={() => setFilter(f)}
                            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors border ${filter === f ? 'bg-primary/20 text-primary border-primary/40' : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-gray-200'}`}
                        >
                            {f}
                        </button>
                    ))}
                </div>
            </div>

            <div className="bg-surface rounded-xl border border-slate-700/50 overflow-hidden shadow-lg">
                <div className="divide-y divide-slate-700/50">
                    {filteredAlerts.length === 0 ? (
                        <div className="p-8 text-center text-slate-500">No alerts found.</div>
                    ) : (
                        filteredAlerts.map(alert => (
                            <div key={alert.id} className="p-4 hover:bg-slate-800/30 transition-colors flex items-start gap-4 group">
                                <div className="mt-1 p-2 rounded-full bg-slate-800 border border-slate-700 group-hover:bg-slate-700 transition-colors">
                                    {getIcon(alert.severity)}
                                </div>
                                <div className="flex-1">
                                    <div className="flex items-center justify-between mb-1">
                                        <h4 className="text-sm font-medium text-gray-200">{alert.message}</h4>
                                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${getBadgeStyle(alert.severity)}`}>
                                            {alert.severity}
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-4 text-xs text-slate-500">
                                        <span className="font-mono">{alert.time}</span>
                                        <span>•</span>
                                        <span>Source: {alert.source}</span>
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
}
