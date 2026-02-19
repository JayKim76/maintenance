import { useState } from 'react';
import { Settings as SettingsIcon, Database, Moon, Server, CheckCircle, XCircle, Loader, Link } from 'lucide-react';
import { getApiUrl } from '../utils/api';

export default function Settings() {
    const [connInfo, setConnInfo] = useState({
        host: 'localhost',
        port: '1521',
        service_name: 'ORCLPDB1',
        username: 'system',
        password: '',
        mode: 'SERVICE_NAME' // SERVICE_NAME or SID
    });
    const [serverUrl, setServerUrl] = useState(getApiUrl());
    const [testStatus, setTestStatus] = useState(null); // null, 'loading', 'success', 'error'
    const [testMessage, setTestMessage] = useState('');

    // Server Connection Test State
    const [serverTestStatus, setServerTestStatus] = useState(null);
    const [serverTestMessage, setServerTestMessage] = useState('');

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setConnInfo(prev => ({ ...prev, [name]: value }));
    };

    const handleModeChange = (mode) => {
        setConnInfo(prev => ({ ...prev, mode }));
    };

    const handleServerUrlChange = (e) => {
        setServerUrl(e.target.value);
    };

    const saveServerUrl = () => {
        localStorage.setItem('server_url', serverUrl);
        setServerTestStatus('success');
        setServerTestMessage('Server URL saved. Reloading...');
        setTimeout(() => window.location.reload(), 1000);
    };

    const testServerConnection = async () => {
        setServerTestStatus('loading');
        setServerTestMessage('');
        try {
            const res = await fetch(`${serverUrl}/`);
            if (res.ok) {
                setServerTestStatus('success');
                setServerTestMessage('Connected to Monitoring Server');
            } else {
                throw new Error('Server responded with error');
            }
        } catch (e) {
            setServerTestStatus('error');
            setServerTestMessage('Failed to connect to Monitoring Server');
        }
    };

    const handleTestConnection = async () => {
        setTestStatus('loading');
        setTestMessage('');

        try {
            const res = await fetch(`${getApiUrl()}/api/settings/test-connection`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(connInfo)
            });
            const data = await res.json();

            if (data.status === 'success') {
                setTestStatus('success');
                setTestMessage(data.message);
            } else {
                setTestStatus('error');
                setTestMessage(data.message);
            }
        } catch (err) {
            setTestStatus('error');
            setTestMessage('Network Error: Could not reach backend server.');
        }
    };

    return (
        <div className="space-y-6 max-w-3xl mx-auto pb-10">
            <h2 className="text-2xl font-bold text-gray-100 flex items-center gap-2">
                <SettingsIcon className="text-secondary" /> Configuration
            </h2>

            <div className="space-y-4">
                {/* Server Connection Settings */}
                <Section title="Monitoring Server" icon={<Link className="text-secondary" />}>
                    <div className="flex gap-4 items-end">
                        <div className="flex-1">
                            <Input
                                label="Server URL"
                                name="serverUrl"
                                value={serverUrl}
                                onChange={handleServerUrlChange}
                                placeholder="http://localhost:8000"
                            />
                        </div>
                        <button onClick={testServerConnection} disabled={serverTestStatus === 'loading'} className="mb-[2px] px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg transition-colors disabled:opacity-50">
                            {serverTestStatus === 'loading' ? <Loader className="w-4 h-4 animate-spin" /> : 'Test'}
                        </button>
                        <button onClick={saveServerUrl} className="mb-[2px] px-4 py-2 bg-primary hover:bg-primary/90 text-background font-bold rounded-lg transition-colors">
                            Save
                        </button>
                    </div>
                    {serverTestMessage && (
                        <div className={`mt-4 p-3 rounded-lg text-sm flex items-start gap-2 ${serverTestStatus === 'success' ? 'bg-secondary/10 text-secondary border border-secondary/20' : 'bg-danger/10 text-danger border border-danger/20'}`}>
                            {serverTestStatus === 'success' ? <CheckCircle className="w-4 h-4 mt-0.5" /> : <XCircle className="w-4 h-4 mt-0.5" />}
                            <span>{serverTestMessage}</span>
                        </div>
                    )}
                </Section>

                {/* Connection Settings */}
                <Section title="Database Connection" icon={<Database className="text-primary" />}>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <Input label="Host" name="host" value={connInfo.host} onChange={handleInputChange} />
                        <Input label="Port" name="port" value={connInfo.port} onChange={handleInputChange} />

                        <div className="md:col-span-2">
                            <label className="block text-xs font-medium text-slate-400 mb-1.5">Connection Type</label>
                            <div className="flex gap-4 mb-2">
                                <label className="flex items-center gap-2 cursor-pointer">
                                    <input
                                        type="radio"
                                        name="mode"
                                        value="SERVICE_NAME"
                                        checked={connInfo.mode === 'SERVICE_NAME'}
                                        onChange={() => handleModeChange('SERVICE_NAME')}
                                        className="accent-primary"
                                    />
                                    <span className="text-sm text-gray-300">Service Name</span>
                                </label>
                                <label className="flex items-center gap-2 cursor-pointer">
                                    <input
                                        type="radio"
                                        name="mode"
                                        value="SID"
                                        checked={connInfo.mode === 'SID'}
                                        onChange={() => handleModeChange('SID')}
                                        className="accent-primary"
                                    />
                                    <span className="text-sm text-gray-300">SID</span>
                                </label>
                            </div>
                        </div>

                        <Input
                            label={connInfo.mode === 'SERVICE_NAME' ? "Service Name" : "SID"}
                            name="service_name"
                            value={connInfo.service_name}
                            onChange={handleInputChange}
                        />
                        <Input label="Username" name="username" value={connInfo.username} onChange={handleInputChange} />
                        <Input label="Password" name="password" type="password" value={connInfo.password} onChange={handleInputChange} />
                    </div>

                    {testMessage && (
                        <div className={`mt-4 p-3 rounded-lg text-sm flex items-start gap-2 ${testStatus === 'success' ? 'bg-secondary/10 text-secondary border border-secondary/20' : 'bg-danger/10 text-danger border border-danger/20'}`}>
                            {testStatus === 'success' ? <CheckCircle className="w-4 h-4 mt-0.5" /> : <XCircle className="w-4 h-4 mt-0.5" />}
                            <span>{testMessage}</span>
                        </div>
                    )}

                    <div className="mt-4 flex justify-end">
                        <button
                            onClick={handleTestConnection}
                            disabled={testStatus === 'loading'}
                            className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary/90 text-background font-bold rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {testStatus === 'loading' && <Loader className="w-4 h-4 animate-spin" />}
                            Test Connection
                        </button>
                    </div>
                </Section>

                {/* Display Settings */}
                <Section title="Display Preferences" icon={<Moon className="text-accent" />}>
                    <Toggle label="Dark Mode" checked={true} />
                    <Toggle label="Show Animations" checked={true} />
                    <Toggle label="Compact Mode" checked={false} />
                </Section>

                {/* System Settings */}
                <Section title="System" icon={<Server className="text-secondary" />}>
                    <Toggle label="Mock Mode (Demo)" checked={true} sub="Use simulated data instead of real database connection" />
                    <div className="mt-4">
                        <label className="block text-xs text-slate-400 mb-1">Refresh Interval (sec)</label>
                        <input type="range" min="1" max="10" defaultValue="2" className="w-full accent-primary h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer" />
                        <div className="flex justify-between text-xs text-slate-500 mt-1">
                            <span>1s</span>
                            <span>5s</span>
                            <span>10s</span>
                        </div>
                    </div>
                </Section>
            </div>
        </div>
    );
}

function Section({ title, icon, children }) {
    return (
        <div className="bg-surface rounded-xl border border-slate-700/50 p-6 shadow-lg">
            <div className="flex items-center gap-3 mb-6 border-b border-slate-700/50 pb-4">
                <div className="p-2 bg-slate-800 rounded-lg text-slate-300">{icon}</div>
                <h3 className="text-lg font-semibold text-gray-200">{title}</h3>
            </div>
            {children}
        </div>
    );
}

function Input({ label, name, value, onChange, type = "text" }) {
    return (
        <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">{label}</label>
            <input
                type={type}
                name={name}
                value={value}
                onChange={onChange}
                className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-primary/50 transition-colors"
            />
        </div>
    );
}

function Toggle({ label, checked, sub }) {
    return (
        <div className="flex items-center justify-between py-3">
            <div>
                <div className="text-sm font-medium text-gray-300">{label}</div>
                {sub && <div className="text-xs text-slate-500">{sub}</div>}
            </div>
            <div className={`w-11 h-6 flex items-center rounded-full p-1 cursor-pointer transition-colors ${checked ? 'bg-primary' : 'bg-slate-700'}`}>
                <div className={`bg-white w-4 h-4 rounded-full shadow-md transform transition-transform ${checked ? 'translate-x-5' : 'translate-x-0'}`}></div>
            </div>
        </div>
    );
}
