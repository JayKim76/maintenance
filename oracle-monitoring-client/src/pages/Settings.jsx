import { useState } from 'react';
import { Settings as SettingsIcon, Link, Moon, Server, Loader, CheckCircle, XCircle, Lock } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { getApiUrl } from '../utils/api';

export default function Settings() {
    const [serverUrl, setServerUrl] = useState(getApiUrl());
    const [serverTestStatus, setServerTestStatus] = useState(null);
    const [serverTestMessage, setServerTestMessage] = useState('');
    const [darkMode, setDarkMode] = useState(true);
    const [showAnimations, setShowAnimations] = useState(true);
    const [compactMode, setCompactMode] = useState(false);
    const { role, hasPermission } = useAuth();

    const canModifySettings = hasPermission('modify_settings');

    const handleServerUrlChange = (e) => {
        setServerUrl(e.target.value);
    };

    const saveServerUrl = () => {
        if (!canModifySettings) return;
        localStorage.setItem('server_url', serverUrl);
        setServerTestStatus('success');
        setServerTestMessage('Server URL saved. Reloading...');
        setTimeout(() => window.location.reload(), 1000);
    };

    const testServerConnection = async () => {
        setServerTestStatus('loading');
        setServerTestMessage('');
        try {
            const res = await fetch(`${serverUrl}/api/status`, {
                headers: { 'X-Role': role }
            });
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

    return (
        <div className="space-y-6 max-w-3xl mx-auto pb-10">
            <div className="flex flex-col">
                <h2 className="text-2xl font-bold text-gray-100 flex items-center gap-2">
                    <SettingsIcon className="text-secondary" /> Configuration
                </h2>
                {!canModifySettings && (
                    <span className="text-xs text-danger flex items-center gap-1 mt-1 font-medium bg-danger/10 px-2 py-0.5 rounded border border-danger/20 w-fit">
                        <Lock className="w-3 h-3" /> {role} 역할은 시스템 설정을 변경할 권한이 없습니다.
                    </span>
                )}
            </div>

            <div className="space-y-4">
                {/* Server Connection Settings */}
                <Section title="Monitoring Server" icon={<Link className="text-secondary" />} restricted={!canModifySettings}>
                    <div className="flex gap-4 items-end">
                        <div className="flex-1">
                            <Input
                                label="Server URL"
                                name="serverUrl"
                                value={serverUrl}
                                onChange={handleServerUrlChange}
                                placeholder="http://localhost:8000"
                                disabled={!canModifySettings}
                            />
                        </div>
                        <button
                            onClick={testServerConnection}
                            disabled={serverTestStatus === 'loading'}
                            className="mb-[2px] px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg transition-colors disabled:opacity-50"
                        >
                            {serverTestStatus === 'loading' ? <Loader className="w-4 h-4 animate-spin" /> : 'Test'}
                        </button>
                        <button
                            onClick={saveServerUrl}
                            disabled={!canModifySettings}
                            className={`mb-[2px] px-4 py-2 bg-primary hover:bg-primary/90 text-background font-bold rounded-lg transition-colors ${!canModifySettings ? 'opacity-50 cursor-not-allowed' : ''}`}
                        >
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

                {/* Display Settings */}
                <Section title="Display Preferences" icon={<Moon className="text-accent" />}>
                    <Toggle label="Dark Mode" checked={darkMode} onChange={setDarkMode} />
                    <Toggle label="Show Animations" checked={showAnimations} onChange={setShowAnimations} />
                    <Toggle label="Compact Mode" checked={compactMode} onChange={setCompactMode} />
                </Section>

                {/* System Settings */}
                <Section title="System" icon={<Server className="text-secondary" />} restricted={!canModifySettings}>
                    <div className="mt-4">
                        <label className="block text-xs text-slate-400 mb-1">Refresh Interval (sec)</label>
                        <input
                            type="range"
                            min="1"
                            max="10"
                            defaultValue="2"
                            disabled={!canModifySettings}
                            className={`w-full accent-primary h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer ${!canModifySettings ? 'opacity-50 cursor-not-allowed' : ''}`}
                        />
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

function Section({ title, icon, children, restricted }) {
    return (
        <div className={`bg-surface rounded-xl border border-slate-700/50 p-6 shadow-lg relative ${restricted ? 'opacity-80' : ''}`}>
            {restricted && (
                <div className="absolute top-4 right-4 text-danger opacity-50">
                    <Lock size={16} />
                </div>
            )}
            <div className="flex items-center gap-3 mb-6 border-b border-slate-700/50 pb-4">
                <div className="p-2 bg-slate-800 rounded-lg text-slate-300">{icon}</div>
                <h3 className="text-lg font-semibold text-gray-200">{title}</h3>
            </div>
            {children}
        </div>
    );
}

function Input({ label, name, value, onChange, type = 'text', placeholder = '', disabled = false }) {
    return (
        <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">{label}</label>
            <input
                type={type}
                name={name}
                value={value}
                onChange={onChange}
                placeholder={placeholder}
                disabled={disabled}
                className={`w-full bg-slate-900/50 border border-slate-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-primary/50 transition-colors ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
            />
        </div>
    );
}

function Toggle({ label, checked, onChange, sub, disabled = false }) {
    return (
        <div className="flex items-center justify-between py-3">
            <div>
                <div className="text-sm font-medium text-gray-300">{label}</div>
                {sub && <div className="text-xs text-slate-500">{sub}</div>}
            </div>
            <button
                type="button"
                onClick={() => !disabled && onChange(!checked)}
                disabled={disabled}
                className={`w-11 h-6 flex items-center rounded-full p-1 transition-colors ${checked ? 'bg-primary' : 'bg-slate-700'} ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
            >
                <div className={`bg-white w-4 h-4 rounded-full shadow-md transform transition-transform ${checked ? 'translate-x-5' : 'translate-x-0'}`} />
            </button>
        </div>
    );
}
