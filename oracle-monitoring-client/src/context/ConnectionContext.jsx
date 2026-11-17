import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { getApiUrl } from '../utils/api';

const ConnectionContext = createContext();

export function ConnectionProvider({ children }) {
    const [connectionInfo, setConnectionInfo] = useState({
        connected: false,
        dsn: null,
        user: null
    });

    const checkStatus = useCallback(async () => {
        try {
            const res = await fetch(`${getApiUrl()}/api/settings/status`);
            const data = await res.json();
            setConnectionInfo(data);
        } catch {
            setConnectionInfo({ connected: false, dsn: null, user: null });
        }
    }, []);

    const disconnect = useCallback(async () => {
        try {
            const res = await fetch(`${getApiUrl()}/api/settings/disconnect`, {
                method: 'POST',
                headers: {
                    'X-Role': localStorage.getItem('userRole') || 'ADMIN'
                }
            });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                setConnectionInfo({ connected: false, dsn: null, user: null });
            } else {
                console.error('Disconnect backend response error:', data);
                // Force local disconnect state anyway if backend failed
                setConnectionInfo({ connected: false, dsn: null, user: null });
            }
        } catch (err) {
            console.error('Disconnect failed:', err);
            setConnectionInfo({ connected: false, dsn: null, user: null });
        }
    }, []);

    const refreshStatus = useCallback(() => {
        checkStatus();
    }, [checkStatus]);

    useEffect(() => {
        checkStatus();
        const interval = setInterval(checkStatus, 10000);
        return () => clearInterval(interval);
    }, [checkStatus]);

    return (
        <ConnectionContext.Provider value={{ ...connectionInfo, disconnect, refreshStatus }}>
            {children}
        </ConnectionContext.Provider>
    );
}

export function useConnection() {
    return useContext(ConnectionContext);
}
