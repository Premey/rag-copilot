import React, { useState } from 'react';

/**
 * Collapsible list of retrieved source chunks.
 */
export default function SourcesList({ sources }) {
    const [expanded, setExpanded] = useState(false);

    if (!sources || sources.length === 0) return null;

    return (
        <div className="sources-panel">
            <button
                className="sources-toggle"
                onClick={() => setExpanded((v) => !v)}
                aria-expanded={expanded}
            >
                <span className="sources-icon">📄</span>
                {sources.length} source{sources.length !== 1 ? 's' : ''}
                <span className={`chevron ${expanded ? 'open' : ''}`}>›</span>
            </button>

            {expanded && (
                <ul className="sources-list">
                    {sources.map((src, i) => (
                        <li key={src.chunk_id || i} className="source-item">
                            <div className="source-header">
                                <span className="source-title">{src.title}</span>
                                <span
                                    className={`score-badge ${src.score >= 0.75
                                            ? 'score-high'
                                            : src.score >= 0.55
                                                ? 'score-mid'
                                                : 'score-low'
                                        }`}
                                >
                                    {(src.score * 100).toFixed(0)}%
                                </span>
                            </div>
                            <p className="source-text">{src.chunk_text}</p>
                            <span className="source-docid">{src.doc_id}</span>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}
