import { useState, useEffect } from 'react';
import { useAuth, Role } from '../hooks/useAuth';
import { useNavigate, useLocation } from 'react-router-dom';
import { useConnection } from '../context/ConnectionContext';
import { Plug, LayoutDashboard, Database, Terminal, AlertCircle, Activity, Settings, User, Power } from 'lucide-react';
import { getApiUrl } from '../utils/api';

export default function Layout({ children }) {
    const navigate = useNavigate();
    const location = useLocation();
    const { connected, dsn, user, disconnect } = useConnection();
    const { role, setRole } = useAuth();
    const [alertCount, setAlertCount] = useState(null);

    useEffect(() => {
        let cancelled = false;
        const fetchAlertCount = async () => {
            try {
                const res = await fetch(`${getApiUrl()}/api/alerts/history`, {
                    headers: { 'X-Role': role }
                });
                if (!res.ok) return;
                const data = await res.json();
                if (!cancelled) setAlertCount(Array.isArray(data) ? data.length : 0);
            } catch {
                // 연결 안 된 상태에서는 뱃지 숨김
            }
        };
        fetchAlertCount();
        const interval = setInterval(fetchAlertCount, 30000);
        return () => { cancelled = true; clearInterval(interval); };
    }, [role, connected]);

    const handleDisconnect = async () => {
        await disconnect();
    };

    const isActive = (path) => location.pathname === path;

    return (
        <div className="flex h-screen bg-background text-gray-100 font-sans overflow-hidden">
            {/* Sidebar */}
            <aside className="w-16 md:w-64 bg-surface border-r border-slate-700 flex flex-col transition-all duration-300">
                <div className="h-16 flex items-center justify-center md:justify-start px-4 gap-3 border-b border-slate-700/50">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-primary to-secondary text-surface flex items-center justify-center font-bold shadow-lg shadow-primary/20">O</div>
                    <span className="hidden md:block font-bold text-lg tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-gray-100 to-gray-400">Oracle Monitor</span>
                </div>

                <nav className="flex-1 mt-6 px-3 space-y-1">
                    <NavItem
                        icon={<Plug size={20} />}
                        label="Connections"
                        active={isActive('/connections')}
                        onClick={() => navigate('/connections')}
                    />
                    <NavItem
                        icon={<LayoutDashboard size={20} />}
                        label="Dashboard"
                        active={isActive('/')}
                        onClick={() => navigate('/')}
                    />
                    <NavItem
                        icon={<Database size={20} />}
                        label="Performance"
                        active={isActive('/performance')}
                        onClick={() => navigate('/performance')}
                    />
                    <NavItem
                        icon={<Terminal size={20} />}
                        label="Editor"
                        active={isActive('/editor')}
                        onClick={() => navigate('/editor')}
                    />
                    <NavItem
                        icon={<AlertCircle size={20} />}
                        label="Alerts"
                        active={isActive('/alerts')}
                        badge={alertCount > 0 ? String(alertCount > 99 ? '99+' : alertCount) : null}
                        onClick={() => navigate('/alerts')}
                    />
                    <NavItem
                        icon={<Activity size={20} />}
                        label="Health Check"
                        active={isActive('/healthcheck')}
                        onClick={() => navigate('/healthcheck')}
                    />
                    <NavItem
                        icon={<Settings size={20} />}
                        label="Settings"
                        active={isActive('/settings')}
                        onClick={() => navigate('/settings')}
                    />
                </nav>

                <div className="p-4 border-t border-slate-700">
                    <div className="flex flex-col gap-2">
                        <span className="text-[10px] uppercase font-bold text-slate-500 px-3">Active Role</span>
                        <select 
                            value={role} 
                            onChange={(e) => setRole(e.target.value)}
                            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-gray-300 outline-none focus:ring-1 focus:ring-primary/50 cursor-pointer w-full"
                        >
                            <option value={Role.ADMIN}>ADMIN (Full)</option>
                            <option value={Role.DBA}>DBA (SQL Execution)</option>
                            <option value={Role.OPERATOR}>OPERATOR (Read Only)</option>
                            <option value={Role.VIEWER}>VIEWER (No SQL)</option>
                        </select>
                    </div>
                </div>
            </aside>

            {/* Main Content */}
            <div className="flex-1 flex flex-col min-w-0 bg-background/50 relative">
                {/* Header */}
                <header className="h-16 bg-surface/30 backdrop-blur-md border-b border-slate-700/50 flex items-center justify-between px-6 z-10 sticky top-0">
                    <div className="flex items-center gap-4">
                        <h2 className="text-xl font-semibold text-gray-100">
                            {location.pathname === '/' && 'Command Center'}
                            {location.pathname === '/performance' && 'The Lab'}
                            {location.pathname === '/alerts' && 'Alert History'}
                            {location.pathname === '/settings' && 'Configuration'}
                            {location.pathname === '/connections' && 'Database Connection'}
                            {location.pathname === '/healthcheck' && 'DB Health Check'}
                        </h2>
                    </div>

                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-2 mr-4">
                            <User className="w-4 h-4 text-primary" />
                            <span className="text-xs font-semibold text-primary px-2 py-0.5 rounded bg-primary/10 border border-primary/20">
                                {role}
                            </span>
                        </div>
                        <div className="h-6 w-px bg-slate-700 mx-2"></div>
                        {connected ? (
                            <div className="flex items-center gap-2">
                                <span className="px-3 py-1 rounded-full bg-secondary/10 text-secondary text-xs font-medium border border-secondary/20 flex items-center gap-2 shadow-sm shadow-secondary/5">
                                    <span className="w-2 h-2 rounded-full bg-secondary animate-pulse shadow-[0_0_8px_rgba(132,204,22,0.6)]"></span>
                                    {user}@{dsn}
                                </span>
                                <button onClick={handleDisconnect} title="Disconnect" className="p-1.5 rounded-lg bg-slate-800 hover:bg-danger/20 hover:text-danger text-slate-400 transition-colors">
                                    <Power className="w-4 h-4" />
                                </button>
                            </div>
                        ) : (
                            <span onClick={() => navigate('/connections')} className="px-3 py-1 rounded-full bg-slate-800 text-slate-400 text-xs font-medium border border-slate-700 flex items-center gap-2 cursor-pointer hover:border-primary/50 hover:text-primary transition-colors">
                                <span className="w-2 h-2 rounded-full bg-slate-500"></span>
                                NOT CONNECTED
                            </span>
                        )}
                    </div>
                </header>

                {/* Scrollable Content */}
                <main className="flex-1 overflow-auto p-6 custom-scrollbar relative">
                    <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-primary/5 via-transparent to-transparent pointer-events-none"></div>
                    {children}
                </main>
            </div>
        </div>
    );
}

function NavItem({ icon, label, active, badge, onClick }) {
    return (
        <button onClick={onClick} className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 group ${active ? 'bg-primary/10 text-primary border border-primary/20 shadow-[0_0_15px_-3px_rgba(6,182,212,0.15)]' : 'hover:bg-slate-800/50 text-slate-400 hover:text-gray-200'}`}>
            <div className={`transition-transform duration-200 ${active ? 'scale-110' : 'group-hover:scale-105'}`}>
                {icon}
            </div>
            <span className="hidden md:block text-sm font-medium">{label}</span>
            {badge && <span className="ml-auto bg-danger text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full shadow-sm shadow-danger/40">{badge}</span>}
        </button>
    );
}
