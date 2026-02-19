import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Database, Activity, Clock, Server, Layers } from 'lucide-react';
import { getApiUrl } from '../utils/api';

export default function SqlDetails() {
    const { sqlId } = useParams();
    const navigate = useNavigate();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch(`${getApiUrl()}/api/performance/sql/${sqlId}`)
            .then(res => res.json())
            .then(dt => {
                setData(dt);
                setLoading(false);
            })
            .catch(err => {
                console.error(err);
                setLoading(false);
            });
    }, [sqlId]);

    if (loading) return <div className="p-10 text-center text-slate-500">Loading SQL Details...</div>;
    if (!data) return <div className="p-10 text-center text-danger">SQL Not Found</div>;

    return (
        <div className="space-y-6 max-w-7xl mx-auto pb-10">
            {/* Header */}
            <div className="flex items-center gap-4">
                <button onClick={() => navigate(-1)} className="p-2 hover:bg-slate-800 rounded-full transition-colors text-slate-400 hover:text-white">
                    <ArrowLeft className="w-6 h-6" />
                </button>
                <div>
                    <h2 className="text-2xl font-bold text-gray-100">SQL Details</h2>
                    <div className="text-sm font-mono text-primary">{sqlId}</div>
                </div>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <StatCard label="Executions" value={data.stats.executions.toLocaleString()} icon={<Activity className="text-primary" />} />
                <StatCard label="Elapsed Time (s)" value={data.stats.elapsed_time} icon={<Clock className="text-warning" />} />
                <StatCard label="CPU Time (s)" value={data.stats.cpu_time} icon={<Server className="text-secondary" />} />
                <StatCard label="Buffer Gets" value={data.stats.buffer_gets.toLocaleString()} icon={<Database className="text-accent" />} />
            </div>

            {/* Full SQL Text */}
            <div className="bg-surface rounded-xl border border-slate-700/50 p-6 shadow-lg">
                <h3 className="text-lg font-semibold text-gray-100 mb-4 flex items-center gap-2">
                    <Layers className="w-5 h-5 text-slate-400" /> Full SQL Text
                </h3>
                <pre className="bg-slate-900/50 p-4 rounded-lg overflow-x-auto text-sm font-mono text-gray-300 leading-relaxed custom-scrollbar">
                    {data.sql_text}
                </pre>
            </div>

            {/* Execution Plan */}
            <div className="bg-surface rounded-xl border border-slate-700/50 p-6 shadow-lg overflow-hidden">
                <h3 className="text-lg font-semibold text-gray-100 mb-4">Execution Plan (Mock)</h3>
                <div className="overflow-x-auto custom-scrollbar">
                    <table className="w-full text-left text-sm text-gray-300">
                        <thead className="bg-slate-800/50 text-slate-400 uppercase text-xs">
                            <tr>
                                <th className="px-4 py-3 text-center">ID</th>
                                <th className="px-4 py-3">Operation</th>
                                <th className="px-4 py-3">Object</th>
                                <th className="px-4 py-3 text-right">Cost</th>
                                <th className="px-4 py-3 text-right">Card</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-700/50">
                            {data.plan.map((step) => (
                                <tr key={step.id} className="hover:bg-slate-800/30 transition-colors">
                                    <td className="px-4 py-2 text-center text-slate-500">{step.id}</td>
                                    <td className="px-4 py-2 font-mono">
                                        <div style={{ paddingLeft: `${(step.parent_id !== null ? 2 : 0)}em` }}>
                                            {step.parent_id !== null && <span className="text-slate-600 mr-2">└─</span>}
                                            <span className={step.operation.includes('ACCESS') ? 'text-secondary' : 'text-gray-200'}>
                                                {step.operation}
                                            </span>
                                            {step.options && <span className="ml-2 text-xs text-slate-400">{step.options}</span>}
                                        </div>
                                    </td>
                                    <td className="px-4 py-2 text-primary">{step.object}</td>
                                    <td className="px-4 py-2 text-right">{step.cost}</td>
                                    <td className="px-4 py-2 text-right">{step.cardinality}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}

function StatCard({ label, value, icon }) {
    return (
        <div className="bg-surface p-4 rounded-xl border border-slate-700/50 shadow-md flex items-center gap-4">
            <div className="p-3 bg-slate-800 rounded-lg">{icon}</div>
            <div>
                <div className="text-xs text-slate-400 uppercase tracking-wide">{label}</div>
                <div className="text-xl font-bold text-gray-100">{value}</div>
            </div>
        </div>
    );
}
