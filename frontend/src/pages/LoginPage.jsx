import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function LoginPage() {
    const { login } = useAuth();
    const navigate = useNavigate();

    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    async function handleSubmit(e) {
        e.preventDefault();
        if (!email || !password) return;
        setLoading(true);
        setError('');
        try {
            await login(email, password);
            navigate('/app');
        } catch (err) {
            setError(err.message || 'Login failed. Check your credentials.');
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="auth-bg">
            <div className="auth-card">
                {/* Logo / branding */}
                <div className="brand">
                    <div className="brand-icon">✦</div>
                    <h1 className="brand-name">RAG Copilot</h1>
                    <p className="brand-sub">CloudDesk AI Knowledge Assistant</p>
                </div>

                <form className="auth-form" onSubmit={handleSubmit} noValidate>
                    <div className="field">
                        <label htmlFor="email">Email</label>
                        <input
                            id="email"
                            type="email"
                            autoComplete="email"
                            placeholder="you@company.com"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            disabled={loading}
                            required
                        />
                    </div>

                    <div className="field">
                        <label htmlFor="password">Password</label>
                        <input
                            id="password"
                            type="password"
                            autoComplete="current-password"
                            placeholder="••••••••"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            disabled={loading}
                            required
                        />
                    </div>

                    {error && (
                        <div className="error-banner" role="alert">
                            <span className="error-icon">⚠</span> {error}
                        </div>
                    )}

                    <button
                        type="submit"
                        className="btn-primary btn-full"
                        disabled={loading || !email || !password}
                    >
                        {loading ? <span className="spinner-sm" /> : 'Sign in'}
                    </button>
                </form>

                <p className="auth-footer">
                    Don&apos;t have an account?{' '}
                    <Link to="/signup" className="link">
                        Create one
                    </Link>
                </p>
            </div>
        </div>
    );
}
