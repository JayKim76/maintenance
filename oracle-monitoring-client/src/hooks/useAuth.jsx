import React, { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext();

export const Role = {
    ADMIN: "ADMIN",
    DBA: "DBA",
    OPERATOR: "OPERATOR",
    VIEWER: "VIEWER"
};

const PERMISSIONS = {
    [Role.ADMIN]: ["view_metrics", "view_alerts", "execute_sql", "execute_dml", "modify_settings"],
    [Role.DBA]: ["view_metrics", "view_alerts", "execute_sql", "execute_dml"],
    [Role.OPERATOR]: ["view_metrics", "view_alerts", "execute_sql"],
    [Role.VIEWER]: ["view_metrics", "view_alerts"]
};

export const AuthProvider = ({ children }) => {
    // Default to ADMIN for development convenience, but normally would come from login
    const [role, setRole] = useState(() => {
        return localStorage.getItem('userRole') || Role.ADMIN;
    });

    useEffect(() => {
        localStorage.setItem('userRole', role);
    }, [role]);

    const hasPermission = (permission) => {
        return PERMISSIONS[role]?.includes(permission) || false;
    };

    return (
        <AuthContext.Provider value={{ role, setRole, hasPermission }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};
