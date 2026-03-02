import React from 'react';

const SUGGESTIONS = [
    'How do I reset my API key?',
    'What are the billing plans available?',
    'How do I enable two-factor authentication?',
    'What are the SLA response times for critical tickets?',
    'How do I set up GitHub integration?',
    'How do webhooks work in CloudDesk?',
];

export default function EmptyState({ onSuggest }) {
    return (
        <div className="empty-state">
            <div className="empty-icon">✦</div>
            <h2 className="empty-title">How can I help you today?</h2>
            <p className="empty-sub">
                Ask anything about CloudDesk — billing, API keys, integrations, SLAs and more.
            </p>
            {onSuggest && (
                <div className="suggestions-grid">
                    {SUGGESTIONS.map((s) => (
                        <button
                            key={s}
                            className="suggestion-chip"
                            onClick={() => onSuggest(s)}
                        >
                            {s}
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
}
