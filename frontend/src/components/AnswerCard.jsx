import React from 'react';

/**
 * Renders the AI answer with different styles based on status:
 * - "ok"          → normal answer text
 * - "low_context" → amber warning card
 * - "error"       → red error card
 */
export default function AnswerCard({ result }) {
    const { answer, status, latency_ms, model_used } = result;

    if (status === 'low_context') {
        return (
            <div className="answer-card answer-low-ctx">
                <div className="answer-status-badge low-ctx-badge">
                    <span>⚠</span> Low context
                </div>
                <p className="answer-text">{answer}</p>
                <div className="answer-meta">
                    <span>{latency_ms}ms</span>
                </div>
            </div>
        );
    }

    if (status === 'error') {
        return (
            <div className="answer-card answer-error">
                <div className="answer-status-badge error-badge">
                    <span>✕</span> Error
                </div>
                <p className="answer-text">{answer}</p>
            </div>
        );
    }

    return (
        <div className="answer-card">
            <p className="answer-text">{answer}</p>
            <div className="answer-meta">
                <span className="meta-model">{model_used}</span>
                <span>{latency_ms}ms</span>
            </div>
        </div>
    );
}
