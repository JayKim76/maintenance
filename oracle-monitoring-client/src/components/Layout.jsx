import { LayoutDashboard, Database, AlertCircle, Settings, Menu, Terminal, Search, Bell, User } from 'lucide-react';
import { useNavigate, useLocation, Link } from 'react-router-dom';

export default function Layout({ children }) {
    const navigate = useNavigate();
    const location = useLocation();

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
                        badge="3"
                        onClick={() => navigate('/alerts')}
                    />
                    <NavItem
                        icon={<Settings size={20} />}
                        label="Settings"
                        active={isActive('/settings')}
                        onClick={() => navigate('/settings')}
                    />
                </nav>

                <div className="p-4 border-t border-slate-700">
                    <NavItem icon={<User size={20} />} label="Admin" />
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
                        </h2>
                    </div>

                    <div className="flex items-center gap-4">
                        <div className="relative hidden md:block group">
                            <Search className="absolute left-3 top-2.5 text-slate-500 w-4 h-4 group-focus-within:text-primary transition-colors" />
                            <input
                                type="text"
                                placeholder="Search instance..."
                                className="bg-slate-800/50 border border-slate-700 rounded-full pl-10 pr-4 py-1.5 text-sm focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50 w-64 transition-all"
                            />
                        </div>
                        <div className="h-6 w-px bg-slate-700 mx-2"></div>
                        <span className="px-3 py-1 rounded-full bg-secondary/10 text-secondary text-xs font-medium border border-secondary/20 flex items-center gap-2 shadow-sm shadow-secondary/5">
                            <span className="w-2 h-2 rounded-full bg-secondary animate-pulse shadow-[0_0_8px_rgba(132,204,22,0.6)]"></span>
                            RUNNING
                        </span>
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
