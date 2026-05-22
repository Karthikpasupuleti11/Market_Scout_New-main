import { useState, useRef, useEffect, forwardRef, useImperativeHandle } from 'react';
import { HiOutlineChat, HiOutlinePaperAirplane, HiOutlineSparkles, HiOutlineRefresh, HiChevronDown, HiChevronUp, HiOutlineLightningBolt, HiOutlineUser } from 'react-icons/hi';
import { indexReport, askRagQuestion } from '../api';
import './ReportAssistant.css';

/* ── Strip residual markdown from RAG responses ──────────────── */
function cleanMarkdown(text) {
    if (!text) return '';
    return text
        .replace(/\*\*(.*?)\*\*/g, '$1')     // **bold**
        .replace(/__(.*?)__/g, '$1')          // __bold__
        .replace(/\*(.*?)\*/g, '$1')          // *italic*
        .replace(/`{1,3}(.*?)`{1,3}/gs, '$1') // `code` / ```code```
        .replace(/^#+\s*/gm, '')              // # headers
        .replace(/^[-*]\s+/gm, '• ')          // - bullets → •
        .trim();
}

const ReportAssistant = forwardRef(({ report }, ref) => {
    const [open, setOpen] = useState(false);
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [indexing, setIndexing] = useState(false);
    const [indexed, setIndexed] = useState(false);
    const [error, setError] = useState('');
    
    const messagesEndRef = useRef(null);
    const containerRef = useRef(null);

    useImperativeHandle(ref, () => ({
        triggerIndex: () => {
            setOpen(true);
            setTimeout(() => {
                containerRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                if (!indexed && !indexing) {
                    handleIndexStart();
                }
            }, 100);
        },
        scrollIntoView: (options) => {
            containerRef.current?.scrollIntoView(options);
        }
    }));

    // Auto-scroll to bottom of messages
    useEffect(() => {
        if (open && messagesEndRef.current) {
            messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages, open]);

    const handleIndexStart = async () => {
        if (indexed || indexing) return;
        
        setIndexing(true);
        setError('');
        try {
            await indexReport(report);
            setIndexed(true);
        } catch (err) {
            setError('Failed to initialize assistant for this report.');
        } finally {
            setIndexing(false);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!input.trim() || loading || indexing) return;

        const userMsg = input.trim();
        setInput('');
        setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
        setLoading(true);

        try {
            const res = await askRagQuestion(userMsg, report.company_name);
            setMessages(prev => [...prev, { role: 'assistant', content: cleanMarkdown(res.answer) }]);
        } catch (err) {
            setMessages(prev => [...prev, { 
                role: 'assistant', 
                content: 'Sorry, I encountered an error while searching the report. Please try again.',
                isError: true
            }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div ref={containerRef} className={`report-assistant ${open ? 'open' : ''}`}>
            <button className="ra-toggle" onClick={() => setOpen(!open)}>
                <div className="ra-toggle-left">
                    <HiOutlineSparkles className="ra-icon" />
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }}>
                        <span style={{ fontWeight: 600 }}>Report Assistant</span>
                        {indexed && !error && (
                            <span className="ra-live-status">
                                <span className="status-dot online ra-live-dot" />
                                Live • Ready to use
                            </span>
                        )}
                    </div>
                </div>
                {open ? <HiChevronUp /> : <HiChevronDown />}
            </button>

            {open && (
                <div className="ra-body fade-in">
                    {!indexed && !indexing && !error ? (
                        <div className="ra-status-pane pre-index-state">
                            <div className="ra-pre-index-icon">
                                <HiOutlineLightningBolt />
                            </div>
                            <h4 className="ra-pre-index-title">Activate Report Assistant</h4>
                            <p className="ra-pre-index-desc">
                                Initialize the AI to ask questions, summarize features, and extract deep strategic insights from the {report.company_name} report.
                            </p>
                            <button className="btn btn-primary pulse-btn" onClick={handleIndexStart}>
                                <HiOutlineSparkles style={{marginRight: '6px'}} />
                                Index and Start
                            </button>
                        </div>
                    ) : indexing ? (
                        <div className="ra-status-pane indexing-state">
                            <div className="ra-scanning-container">
                                <HiOutlineLightningBolt className="ra-scanning-icon" />
                                <div className="ra-scanning-ring"></div>
                                <div className="ra-scanning-ring"></div>
                                <div className="ra-scanning-ring"></div>
                            </div>
                            <span className="ra-indexing-text">Analyzing & vectorizing document...</span>
                        </div>
                    ) : error ? (
                        <div className="ra-status-pane error">
                            <span>{error}</span>
                        </div>
                    ) : (
                        <>
                            <div className="ra-messages">
                                {messages.length === 0 && !loading && (
                                    <div className="ra-welcome-widget">
                                        <div className="ra-welcome-icon">
                                            <HiOutlineSparkles />
                                        </div>
                                        <div className="ra-welcome-text">
                                            <h4>Hi, I'm your Report Assistant</h4>
                                            <p>I've analyzed the report for {report.company_name}. Ask me anything about their strategy, features, or metrics.</p>
                                        </div>
                                    </div>
                                )}
                                {messages.map((msg, i) => (
                                    <div key={i} className={`ra-msg-row ${msg.role}`}>
                                        {msg.role === 'assistant' && (
                                            <div className="ra-avatar assistant-avatar">
                                                <HiOutlineSparkles />
                                            </div>
                                        )}
                                        <div className={`ra-msg-bubble ${msg.isError ? 'error' : ''}`}>
                                            {msg.content}
                                        </div>
                                        {msg.role === 'user' && (
                                            <div className="ra-avatar user-avatar">
                                                <HiOutlineUser />
                                            </div>
                                        )}
                                    </div>
                                ))}
                                {loading && (
                                    <div className="ra-msg-row assistant">
                                        <div className="ra-avatar assistant-avatar">
                                            <HiOutlineSparkles />
                                        </div>
                                        <div className="ra-msg-bubble loading">
                                            <span className="typing-dot" />
                                            <span className="typing-dot" />
                                            <span className="typing-dot" />
                                        </div>
                                    </div>
                                )}
                                <div ref={messagesEndRef} />
                            </div>

                            <div className="ra-suggestions">
                                {['Summarize this report', 'What are the key technical features?', 'List the main products'].map((sug, idx) => (
                                    <button
                                        key={idx}
                                        className="ra-sug-chip"
                                        onClick={() => setInput(sug)}
                                        disabled={loading}
                                    >
                                        <HiOutlineLightningBolt style={{marginRight: '4px'}}/>
                                        {sug}
                                    </button>
                                ))}
                            </div>

                            <form className="ra-input-area" onSubmit={handleSubmit}>
                                <input
                                    type="text"
                                    className="input ra-input"
                                    placeholder="Ask about features, strategy..."
                                    value={input}
                                    onChange={e => setInput(e.target.value)}
                                    disabled={loading}
                                />
                                <button 
                                    type="submit" 
                                    className="btn btn-primary ra-send-btn"
                                    disabled={!input.trim() || loading}
                                >
                                    <HiOutlinePaperAirplane className="send-icon" />
                                </button>
                            </form>
                        </>
                    )}
                </div>
            )}
        </div>
    );
});

export default ReportAssistant;
