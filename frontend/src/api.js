/**
 * API client — all calls to the FastAPI backend.
 * Auth token is read from localStorage on each call.
 */

const API_BASE = '';  // Vite proxy forwards /auth and /rag to localhost:8000

function getToken() {
    return localStorage.getItem('rag_token');
}

async function request(path, options = {}) {
    const token = getToken();
    const headers = {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options.headers || {}),
    };

    const res = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers,
    });

    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
        const message =
            typeof err.detail === 'string'
                ? err.detail
                : Array.isArray(err.detail)
                    ? err.detail.map((e) => e.msg).join(', ')
                    : 'Request failed';
        throw new Error(message);
    }

    return res.json();
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export async function login(email, password) {
    return request('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
    });
}

export async function signup(email, password, fullName) {
    return request('/auth/signup', {
        method: 'POST',
        body: JSON.stringify({ email, password, full_name: fullName }),
    });
}

export async function getMe() {
    return request('/auth/me');
}

// ── RAG ───────────────────────────────────────────────────────────────────────

export async function askQuestion(question, conversationId) {
    return request('/rag/ask', {
        method: 'POST',
        body: JSON.stringify({
            question,
            top_k: 5,
            ...(conversationId ? { conversation_id: conversationId } : {}),
        }),
    });
}

export async function ingestDocs() {
    return request('/rag/ingest', {
        method: 'POST',
        body: JSON.stringify({ force_rebuild: true }),
    });
}

export async function getMetrics() {
    return request('/rag/metrics');
}
