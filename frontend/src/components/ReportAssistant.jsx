import { useState, useRef, useEffect } from 'react';
import { indexReportForRag, askRagQuestion } from '../api';
import { HiOutlineChatAlt2, HiOutlineChevronDown, HiOutlineChevronUp } from 'react-icons/hi';
import './ReportAssistant.css';

/**
 * Collapsible Report Assistant — embeddable chat panel for querying reports.
 * 
 * Props:
 *   report      — the report object (must have company_name, executive_summary, features, all_sources)
 *   companyName — fallback company name if report.company_name is missing
 */
export default function ReportAssistant({ report, companyName, autoOpen }) {
    const [open, setOpen] = useState(false);
    const [indexing, setIndexing] = useState(false);
    const [indexed, setIndexed] = useState(false);
    const [indexError, setIndexError] = useState('');

    const [question, setQuestion] = useState('');
    const [messages, setMessages] = useState([]);
    const [asking, setAsking] = useState(false);

    const messagesEndRef = useRef(null);
    const inputRef = useRef(null);
    const panelRef = useRef(null);

    const handleIndex = async () => {
        setIndexing(true);
        setIndexError('');
        try {
            await indexReportForRag({
                company_name: report.company_name || companyName,
                executive_summary: report.executive_summary || '',
                features: report.features || [],
                all_sources: report.all_sources || [],
            });
            setIndexed(true);
        } catch (err) {
            setIndexError(err.message || 'Failed to index report. Please try again.');
        } finally {
            setIndexing(false);
        }
    };

    // Auto-scroll to bottom on new messages
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, asking]);

    // Focus input when panel opens and is indexed
    useEffect(() => {
        if (open && indexed) {
            inputRef.current?.focus();
        }
    }, [open, indexed]);

    // Reset state when a different report is loaded
    const reportKey = report?.company_name || companyName;
    const prevReportRef = useRef(reportKey);
    useEffect(() => {
        if (prevReportRef.current !== reportKey) {
            prevReportRef.current = reportKey;
            setIndexed(false);
            setIndexing(false);
            setIndexError('');
            setMessages([]);
            setQuestion('');
        }
    }, [reportKey]);

    // Auto-open AND auto-index when triggered by parent (Assistant button)
    const prevAutoOpen = useRef(false);
    useEffect(() => {
        if (autoOpen && !prevAutoOpen.current) {
            setOpen(true);
            if (!indexed && !indexing) {
                handleIndex();
            }
        }
        prevAutoOpen.current = !!autoOpen;
    }, [autoOpen]); // eslint-disable-line react-hooks/exhaustive-deps

    const handleToggle = () => {
        setOpen(prev => {
            const willOpen = !prev;
            if (willOpen) {
                // Scroll into view after React renders the panel
                setTimeout(() => {
                    panelRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }, 100);
            }
            return willOpen;
        });
    };

    const handleAsk = async () => {
        if (!question.trim() || asking) return;
        const userMsg = { type: 'user', text: question };
        setMessages(prev => [...prev, userMsg]);
        setQuestion('');
        setAsking(true);
        try {
            const res = await askRagQuestion(userMsg.text);
            setMessages(prev => [
                ...prev,
                { type: 'bot', text: res.answer, sources: res.sources || [] },
            ]);
        } catch (err) {
            setMessages(prev => [
                ...prev,
                { type: 'bot', text: `Error: ${err.message}`, sources: [] },
            ]);
        }
        setAsking(false);
    };

    const SUGGESTIONS = [
        'Summarize this report',
        'What are the top signals?',
        'Key security concerns?',
        'Most impactful findings?',
    ];

    return (
        <div ref={panelRef} className={`report-assistant ${open ? 'open' : ''}`}>
            {/* ── Toggle Header ─────────────────────────────────── */}
            <button className="ra-toggle" onClick={handleToggle}>
                <div className="ra-toggle-left">
                    <HiOutlineChatAlt2 className="ra-toggle-icon" />
                    <div className="ra-toggle-text">
                        <span className="ra-toggle-title">Report Assistant</span>
                        <span className="ra-toggle-sub">Ask questions about this report using AI</span>
                    </div>
                </div>
                {open ? <HiOutlineChevronUp /> : <HiOutlineChevronDown />}
            </button>

            {/* ── Collapsible Body ─────────────────────────────── */}
            {open && (
                <div className="ra-body fade-in">
                    {/* Index step — shown before report is indexed */}
                    {!indexed && !indexing && (
                        <div className="ra-index-prompt">
                            <div className="ra-index-icon">📄</div>
                            <h4>Index This Report</h4>
                            <p>
                                Click below to analyze and index the report for{' '}
                                <strong>{report.company_name || companyName}</strong> so you can
                                ask questions about it.
                            </p>
                            {indexError && (
                                <div className="ra-error">{indexError}</div>
                            )}
                            <button className="btn btn-primary ra-index-btn" onClick={handleIndex}>
                                <HiOutlineChatAlt2 /> Index &amp; Start Chatting
                            </button>
                        </div>
                    )}

                    {/* Indexing in progress */}
                    {indexing && (
                        <div className="ra-indexing">
                            <div className="ra-indexing-animation">
                                <div className="ra-indexing-ring" />
                                <div className="ra-indexing-icon">🔍</div>
                            </div>
                            <h4>Indexing Report…</h4>
                            <p>Analyzing and embedding report content for intelligent querying</p>
                            <div className="ra-indexing-steps">
                                <div className="ra-step active">
                                    <span className="ra-step-dot" />
                                    Chunking report content
                                </div>
                                <div className="ra-step">
                                    <span className="ra-step-dot" />
                                    Generating embeddings
                                </div>
                                <div className="ra-step">
                                    <span className="ra-step-dot" />
                                    Building search index
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Chat interface — shown after report is indexed */}
                    {indexed && (
                        <div className="ra-chat">
                            <div className="ra-chat-header">
                                <span className="ra-status-dot" />
                                <span>Report indexed — ready to answer questions</span>
                            </div>

                            {/* Messages */}
                            <div className="ra-messages">
                                {messages.length === 0 && !asking && (
                                    <div className="ra-empty">
                                        <div className="ra-empty-icon">💬</div>
                                        <div className="ra-empty-title">Ask anything about this report</div>
                                        <div className="ra-empty-sub">
                                            Try one of these suggestions:
                                        </div>
                                        <div className="ra-suggestions">
                                            {SUGGESTIONS.map((s, i) => (
                                                <button
                                                    key={i}
                                                    className="ra-suggestion-chip"
                                                    onClick={() => {
                                                        setQuestion(s);
                                                        inputRef.current?.focus();
                                                    }}
                                                >
                                                    {s}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {messages.map((msg, i) => (
                                    <div key={i} className={`ra-msg ra-msg--${msg.type}`}>
                                        <div className="ra-msg-label">
                                            {msg.type === 'user' ? 'You' : 'Assistant'}
                                        </div>
                                        <div className={`ra-msg-bubble ra-msg-bubble--${msg.type}`}>
                                            {msg.text}
                                        </div>
                                        {msg.type === 'bot' && msg.sources?.length > 0 && (
                                            <div className="ra-sources">
                                                <span className="ra-sources-label">
                                                    {msg.sources.length} reference{msg.sources.length > 1 ? 's' : ''} used
                                                </span>
                                            </div>
                                        )}
                                    </div>
                                ))}

                                {asking && (
                                    <div className="ra-msg ra-msg--bot">
                                        <div className="ra-msg-label">Assistant</div>
                                        <div className="ra-msg-bubble ra-msg-bubble--bot ra-typing">
                                            <span className="ra-dot" />
                                            <span className="ra-dot" />
                                            <span className="ra-dot" />
                                        </div>
                                    </div>
                                )}

                                <div ref={messagesEndRef} />
                            </div>

                            {/* Input */}
                            <div className="ra-input-row">
                                <input
                                    ref={inputRef}
                                    type="text"
                                    className="ra-input"
                                    placeholder="Ask a question about this report…"
                                    value={question}
                                    onChange={e => setQuestion(e.target.value)}
                                    onKeyDown={e => e.key === 'Enter' && handleAsk()}
                                    disabled={asking}
                                />
                                <button
                                    className="ra-send-btn"
                                    onClick={handleAsk}
                                    disabled={asking || !question.trim()}
                                >
                                    <svg viewBox="0 0 24 24" fill="none"
                                        stroke="currentColor" strokeWidth="2.2"
                                        strokeLinecap="round" strokeLinejoin="round"
                                        className="ra-send-icon"
                                    >
                                        <line x1="22" y1="2" x2="11" y2="13" />
                                        <polygon points="22 2 15 22 11 13 2 9 22 2" />
                                    </svg>
                                    Ask
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
