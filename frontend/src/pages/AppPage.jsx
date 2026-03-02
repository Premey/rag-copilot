import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { askQuestion } from '../api';
import AnswerCard from '../components/AnswerCard';
import SourcesList from '../components/SourcesList';
import EmptyState from '../components/EmptyState';

export default function AppPage() {
    const { user, logout } = useAuth();

    const [question, setQuestion] = useState('');
    const [history, setHistory] = useState([]);   // list of { question, result }
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [conversationId] = useState(() => `conv_${Date.now()}`);

    const inputRef = useRef(null);
    const bottomRef = useRef(null);

    // Scroll to bottom when new messages arrive
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [history, loading]);

    const submit = useCallback(async () => {
        const q = question.trim();
        if (!q || loading) return;
        setQuestion('');
        setError('');
        setLoading(true);

        try {
            const result = await askQuestion(q, conversationId);
            setHistory((prev) => [...prev, { question: q, result }]);
        } catch (err) {
            setError(err.message || 'Something went wrong. Please try again.');
        } finally {
            setLoading(false);
            inputRef.current?.focus();
        }
    }, [question, loading, conversationId]);

    function handleKeyDown(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            submit();
        }
    }

    return (
        <div className="app-layout">
            {/* ── Sidebar ─────────────────────────────────────── */}
            <aside className="sidebar">
                <div className="sidebar-brand">
                    <span className="brand-icon-sm">✦</span>
                    <span>RAG Copilot</span>
                </div>
                <nav className="sidebar-nav">
                    <a className="nav-item active" href="#"><span>💬</span> Chat</a>
                </nav>
                <div className="sidebar-footer">
                    <div className="user-badge">
                        <div className="avatar">{(user?.full_name || user?.email || '?')[0].toUpperCase()}</div>
                        <div className="user-info">
                            <span className="user-name">{user?.full_name || 'User'}</span>
                            <span className="user-email">{user?.email}</span>
                        </div>
                    </div>
                    <button className="btn-logout" onClick={logout} title="Sign out">
                        ⏻
                    </button>
                </div>
            </aside>

            {/* ── Main ────────────────────────────────────────── */}
            <main className="main-panel">
                <header className="main-header">
                    <h2>CloudDesk Knowledge Base</h2>
                    <span className="model-badge">gemini-2.0-flash</span>
                </header>

                <div className="chat-feed">
                    {history.length === 0 && !loading && (
                        <EmptyState onSuggest={(s) => { setQuestion(s); inputRef.current?.focus(); }} />
                    )}

                    {history.map((item, i) => (
                        <div key={i} className="chat-turn">
                            {/* User question bubble */}
                            <div className="bubble-user">
                                <span>{item.question}</span>
                            </div>

                            {/* AI answer card */}
                            <div className="bubble-ai">
                                <AnswerCard result={item.result} />
                                {item.result.sources?.length > 0 && (
                                    <SourcesList sources={item.result.sources} />
                                )}
                            </div>
                        </div>
                    ))}

                    {loading && (
                        <div className="chat-turn">
                            <div className="bubble-thinking">
                                <span className="dot-pulse" />
                                <span className="dot-pulse" />
                                <span className="dot-pulse" />
                            </div>
                        </div>
                    )}

                    {error && (
                        <div className="error-banner chat-error" role="alert">
                            <span className="error-icon">⚠</span> {error}
                            <button className="dismiss-btn" onClick={() => setError('')}>✕</button>
                        </div>
                    )}

                    <div ref={bottomRef} />
                </div>

                {/* ── Input bar ─────────────────────────────────── */}
                <div className="input-bar">
                    <textarea
                        ref={inputRef}
                        className="question-input"
                        id="question-input"
                        placeholder="Ask anything about CloudDesk…  (Enter to send, Shift+Enter for newline)"
                        value={question}
                        onChange={(e) => setQuestion(e.target.value)}
                        onKeyDown={handleKeyDown}
                        disabled={loading}
                        rows={1}
                    />
                    <button
                        className="send-btn"
                        id="send-btn"
                        onClick={submit}
                        disabled={loading || !question.trim()}
                        aria-label="Send question"
                    >
                        {loading ? <span className="spinner-sm" /> : '↑'}
                    </button>
                </div>
            </main>
        </div>
    );
}
