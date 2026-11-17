import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Database, CheckCircle, XCircle, Loader, Save, Trash2, Link2, Plug } from 'lucide-react';
import { getApiUrl } from '../utils/api';
import { useConnection } from '../context/ConnectionContext';

export default function Connections() {
    const { refreshStatus } = useConnection();
    const navigate = useNavigate();
    const [connInfo, setConnInfo] = useState({
        alias: '',
        host: '',
        port: '1521',
        service_name: '',
        username: 'system',
        password: '',
        mode: 'SERVICE_NAME'
    });

    const [savedConnections, setSavedConnections] = useState([]);

    useEffect(() => {
        const loadInitial = async () => {
            try {
                // 1. Fetch saved connections list
                const resSaved = await fetch(`${getApiUrl()}/api/settings/saved-connections`, {
                    headers: { 'X-Role': localStorage.getItem('userRole') || 'ADMIN' }
                });
                if (resSaved.ok) {
                    const data = await resSaved.json();
                    if (Array.isArray(data)) {
                        setSavedConnections(data);
                    }
                }
            } catch (err) {
                console.error("Failed to load saved connections:", err);
            }

            try {
                // 2. Fetch last connection or default saved connection to pre-fill form
                const resLast = await fetch(`${getApiUrl()}/api/settings/last-connection`);
                if (resLast.ok) {
                    const data = await resLast.json();
                    if (data.status === 'success' && data.host) {
                        setConnInfo({
                            alias: data.alias || '',
                            host: data.host || '',
                            port: data.port || '1521',
                            service_name: data.service_name || '',
                            username: data.username || 'system',
                            password: data.password || '',
                            mode: data.mode || 'SERVICE_NAME'
                        });
                    }
                }
            } catch (err) {
                console.error("Failed to load last connection info:", err);
            }
        };
        loadInitial();
    }, []);

    const syncConnectionsToServer = async (updatedConnections) => {
        try {
            await fetch(`${getApiUrl()}/api/settings/saved-connections`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Role': localStorage.getItem('userRole') || 'ADMIN'
                },
                body: JSON.stringify(updatedConnections)
            });
        } catch (err) {
            console.error("Failed to save connections to server:", err);
        }
    };

    const [testStatus, setTestStatus] = useState(null);
    const [testMessage, setTestMessage] = useState('');
    const [connectStatus, setConnectStatus] = useState(null);
    const [connectMessage, setConnectMessage] = useState('');

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setConnInfo(prev => ({ ...prev, [name]: value }));
    };

    const handleModeChange = (mode) => {
        setConnInfo(prev => ({ ...prev, mode }));
    };

    const handleTestConnection = async () => {
        setTestStatus('loading');
        setTestMessage('');
        setConnectStatus(null);
        setConnectMessage('');
        try {
            const res = await fetch(`${getApiUrl()}/api/settings/test-connection`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-Role': localStorage.getItem('userRole') || 'ADMIN' },
                body: JSON.stringify(connInfo)
            });
            const data = await res.json();
            setTestStatus(data.status === 'success' ? 'success' : 'error');
            setTestMessage(data.message);
        } catch (err) {
            setTestStatus('error');
            setTestMessage('Network Error: Could not reach backend server.');
        }
    };

    const handleConnect = async (targetInfo = null) => {
        const payload = (targetInfo && targetInfo.host) ? targetInfo : connInfo;
        setConnectStatus('loading');
        setConnectMessage('');
        setTestStatus(null);
        setTestMessage('');
        try {
            const res = await fetch(`${getApiUrl()}/api/settings/connect`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-Role': localStorage.getItem('userRole') || 'ADMIN' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            setConnectStatus(data.status === 'success' ? 'success' : 'error');
            setConnectMessage(data.message);
            if (data.status === 'success') {
                refreshStatus();
                setTimeout(() => navigate('/'), 800);
            }
        } catch (err) {
            setConnectStatus('error');
            setConnectMessage('Network Error: Could not reach backend server.');
        }
    };

    const saveCurrentConnection = () => {
        const alias = connInfo.alias.trim() || `${connInfo.username}@${connInfo.host}:${connInfo.port}/${connInfo.service_name}`;
        const newConn = { ...connInfo, alias, id: Date.now() };
        const updated = [...savedConnections, newConn];
        setSavedConnections(updated);
        syncConnectionsToServer(updated);
    };

    const deleteSavedConnection = (id) => {
        const updated = savedConnections.filter(c => c.id !== id);
        setSavedConnections(updated);
        syncConnectionsToServer(updated);
    };

    const fillFormWithSavedConnection = (conn) => {
        const { id, ...rest } = conn;
        setConnInfo({ ...connInfo, ...rest });
        setTestStatus(null);
        setTestMessage('');
        setConnectStatus(null);
        setConnectMessage('');
    };

    const loadSavedConnection = (conn) => {
        const { id, ...rest } = conn;
        const newConnInfo = { ...connInfo, ...rest };
        setConnInfo(newConnInfo);
        handleConnect(newConnInfo);
    };

    return (
        <div className="space-y-6 max-w-4xl mx-auto pb-10">
            <h2 className="text-2xl font-bold text-gray-100 flex items-center gap-2">
                <Plug className="text-primary w-6 h-6" /> 데이터베이스 접속
            </h2>

            {/* Connection Form */}
            <div className="bg-surface rounded-xl border border-slate-700/50 p-6 shadow-lg">
                <div className="flex items-center gap-3 mb-6 border-b border-slate-700/50 pb-4">
                    <div className="p-2 bg-slate-800 rounded-lg text-slate-300"><Database className="w-5 h-5 text-primary" /></div>
                    <h3 className="text-lg font-semibold text-gray-200">Connection Info</h3>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="md:col-span-2">
                        <InputField label="별칭 (Alias)" name="alias" value={connInfo.alias} onChange={handleInputChange} placeholder="예: 운영DB, 개발서버, PROD-ORCL" />
                    </div>
                    <InputField label="Host" name="host" value={connInfo.host} onChange={handleInputChange} />
                    <InputField label="Port" name="port" value={connInfo.port} onChange={handleInputChange} />

                    <div className="md:col-span-2">
                        <label className="block text-xs font-medium text-slate-400 mb-1.5">Connection Type</label>
                        <div className="flex gap-4 mb-2">
                            <label className="flex items-center gap-2 cursor-pointer">
                                <input type="radio" name="mode" value="SERVICE_NAME" checked={connInfo.mode === 'SERVICE_NAME'} onChange={() => handleModeChange('SERVICE_NAME')} className="accent-primary" />
                                <span className="text-sm text-gray-300">Service Name</span>
                            </label>
                            <label className="flex items-center gap-2 cursor-pointer">
                                <input type="radio" name="mode" value="SID" checked={connInfo.mode === 'SID'} onChange={() => handleModeChange('SID')} className="accent-primary" />
                                <span className="text-sm text-gray-300">SID</span>
                            </label>
                        </div>
                    </div>

                    <InputField label={connInfo.mode === 'SERVICE_NAME' ? "Service Name" : "SID"} name="service_name" value={connInfo.service_name} onChange={handleInputChange} />
                    <InputField label="Username" name="username" value={connInfo.username} onChange={handleInputChange} />
                    <InputField label="Password" name="password" type="password" value={connInfo.password} onChange={handleInputChange} />
                </div>

                {/* Status messages */}
                {testMessage && (
                    <div className={`mt-4 p-3 rounded-lg text-sm flex items-start gap-2 ${testStatus === 'success' ? 'bg-secondary/10 text-secondary border border-secondary/20' : 'bg-danger/10 text-danger border border-danger/20'}`}>
                        {testStatus === 'success' ? <CheckCircle className="w-4 h-4 mt-0.5" /> : <XCircle className="w-4 h-4 mt-0.5" />}
                        <span>{testMessage}</span>
                    </div>
                )}
                {connectMessage && (
                    <div className={`mt-4 p-3 rounded-lg text-sm flex items-start gap-2 ${connectStatus === 'success' ? 'bg-primary/10 text-primary border border-primary/20' : 'bg-danger/10 text-danger border border-danger/20'}`}>
                        {connectStatus === 'success' ? <CheckCircle className="w-4 h-4 mt-0.5" /> : <XCircle className="w-4 h-4 mt-0.5" />}
                        <span>{connectMessage}</span>
                    </div>
                )}

                {/* Action buttons */}
                <div className="mt-6 flex justify-end gap-3 flex-wrap">
                    <button onClick={saveCurrentConnection} className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 font-bold rounded-lg transition-colors">
                        <Save className="w-4 h-4" /> 저장
                    </button>
                    <button onClick={handleTestConnection} disabled={testStatus === 'loading' || connectStatus === 'loading'} className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 font-bold rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
                        {testStatus === 'loading' && <Loader className="w-4 h-4 animate-spin" />} 테스트
                    </button>
                    <button onClick={() => handleConnect()} disabled={testStatus === 'loading' || connectStatus === 'loading'} className="flex items-center gap-2 px-5 py-2 bg-primary hover:bg-primary/90 text-background font-bold rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-primary/25">
                        {connectStatus === 'loading' && <Loader className="w-4 h-4 animate-spin" />} 접속
                    </button>
                </div>
            </div>

            {/* Saved Connections */}
            {savedConnections.length > 0 && (
                <div className="bg-surface rounded-xl border border-slate-700/50 p-6 shadow-lg">
                    <div className="flex items-center gap-3 mb-6 border-b border-slate-700/50 pb-4">
                        <div className="p-2 bg-slate-800 rounded-lg text-slate-300"><Save className="w-5 h-5 text-secondary" /></div>
                        <h3 className="text-lg font-semibold text-gray-200">저장된 접속 정보</h3>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {savedConnections.map(conn => (
                            <div key={conn.id} className="bg-slate-800/30 border border-slate-700/50 rounded-lg p-4 flex flex-col justify-between hover:border-primary/50 transition-all group shadow-sm bg-gradient-to-br from-slate-800/50 to-slate-900/50 hover:shadow-primary/5 hover:-translate-y-0.5">
                                <div className="mb-4">
                                    <div className="flex items-center justify-between mb-2">
                                        <span className="font-bold text-gray-100 text-sm flex items-center gap-2 truncate">
                                            <Database className="w-4 h-4 text-primary shrink-0" />
                                            <span className="truncate">{conn.alias || `${conn.username}@${conn.host}`}</span>
                                        </span>
                                    </div>
                                    <div className="text-xs text-slate-400 flex items-center gap-2 flex-wrap">
                                        <span className="px-2 py-0.5 bg-slate-800 border border-slate-700 rounded-md">
                                            {conn.username}@{conn.host}:{conn.port}
                                        </span>
                                        <span className="px-2 py-0.5 bg-slate-800 border border-slate-700 rounded-md">
                                            {conn.mode === 'SID' ? `SID: ${conn.service_name}` : `SVC: ${conn.service_name}`}
                                        </span>
                                    </div>
                                </div>
                                <div className="flex gap-2 justify-end mt-auto pt-2 border-t border-slate-700/30">
                                    <button onClick={() => loadSavedConnection(conn)} className="px-3 py-1.5 bg-primary/20 hover:bg-primary text-primary hover:text-slate-900 text-xs font-bold rounded-lg transition-colors shadow-sm flex-1 flex items-center justify-center gap-1">
                                        <Plug className="w-3.5 h-3.5" /> 불러오기 & 접속
                                    </button>
                                    <button onClick={() => fillFormWithSavedConnection(conn)} className="px-3 py-1.5 bg-slate-700/50 hover:bg-slate-600 text-slate-300 text-xs font-semibold rounded-lg transition-colors shadow-sm">
                                        양식 채우기
                                    </button>
                                    <button onClick={() => deleteSavedConnection(conn.id)} className="px-3 py-1.5 bg-slate-700/50 hover:bg-danger hover:text-white text-slate-300 text-xs font-semibold rounded-lg transition-colors shadow-sm" title="삭제">
                                        <Trash2 className="w-4 h-4" />
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

function InputField({ label, name, value, onChange, type = "text", placeholder = "" }) {
    return (
        <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">{label}</label>
            <input type={type} name={name} value={value} onChange={onChange} placeholder={placeholder} className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-slate-600 focus:outline-none focus:border-primary/50 transition-colors" />
        </div>
    );
}
