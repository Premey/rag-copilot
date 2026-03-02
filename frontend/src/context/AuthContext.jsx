import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { login as apiLogin, getMe } from '../api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [token, setToken] = useState(() => localStorage.getItem('rag_token'));
    const [loading, setLoading] = useState(true);

    // On mount: validate stored token
    useEffect(() => {
        if (!token) {
            setLoading(false);
            return;
        }
        getMe()
            .then(setUser)
            .catch(() => {
                localStorage.removeItem('rag_token');
                setToken(null);
            })
            .finally(() => setLoading(false));
    }, [token]);

    const login = useCallback(async (email, password) => {
        const data = await apiLogin(email, password);
        localStorage.setItem('rag_token', data.access_token);
        setToken(data.access_token);
        setUser(data.user);
        return data;
    }, []);

    const logout = useCallback(() => {
        localStorage.removeItem('rag_token');
        setToken(null);
        setUser(null);
    }, []);

    return (
        <AuthContext.Provider value={{ user, token, loading, login, logout }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    return useContext(AuthContext);
}
