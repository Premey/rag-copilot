import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { signup } from '../api';
import { useAuth } from '../context/AuthContext';

export default function SignupPage() {
    const { login } = useAuth();
    const navigate = useNavigate();

    const [fullName, setFullName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    async function handleSubmit(e) {
        e.preventDefault();
        setLoading(true);
        setError('');
        try {
            await signup(email, password, fullName);
            // Auto-login after signup
            await login(email, password);
            navigate('/app');
        } catch (err) {
            setError(err.message || 'Sign-up failed. Please try again.');
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="auth-bg">
            <div className="auth-card">
                <div className="brand">
                    <div className="brand-icon">✦</div>
                    <h1 className="brand-name">RAG Copilot</h1>
                    <p className="brand-sub">Create your account</p>
                </div>

                <form className="auth-form" onSubmit={handleSubmit} noValidate>
                    <div className="field">
                        <label htmlFor="full-name">Full Name</label>
                        <input
                            id="full-name"
                            type="text"
                            placeholder="Jane Doe"
                            value={fullName}
                            onChange={(e) => setFullName(e.target.value)}
                            disabled={loading}
                            required
                        />
                    </div>

                    <div className="field">
                        <label htmlFor="email">Email</label>
                        <input
                            id="email"
                            type="email"
                            placeholder="you@company.com"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            disabled={loading}
                            required
                        />
                    </div>

                    <div className="field">
                        <label htmlFor="password">
                            Password <span className="field-hint">(min 8 chars, 1 uppercase, 1 digit)</span>
                        </label>
                        <input
                            id="password"
                            type="password"
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
                        disabled={loading || !email || !password || !fullName}
                    >
                        {loading ? <span className="spinner-sm" /> : 'Create account'}
                    </button>
                </form>

                <p className="auth-footer">
                    Already have an account?{' '}
                    <Link to="/login" className="link">
                        Sign in
                    </Link>
                </p>
            </div>
        </div>
    );
}
