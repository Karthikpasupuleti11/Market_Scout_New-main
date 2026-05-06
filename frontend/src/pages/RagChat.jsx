import { useState, useRef, useEffect } from "react";
import { uploadRagPDF, askRagQuestion } from "../api";
import "./RagChat.css";

export default function RagChat() {
    const [file, setFile] = useState(null);
    const [question, setQuestion] = useState("");
    const [messages, setMessages] = useState([]);
    const [loading, setLoading] = useState(false);
    const messagesEndRef = useRef(null);

    // Auto-scroll to the bottom of the chat when messages change
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, loading]);

    const handleUpload = async () => {
        if (!file) return alert("Select a file");
        setLoading(true);
        try {
            await uploadRagPDF(file);
            setMessages([]);
            alert("PDF uploaded successfully");
        } catch (err) {
            alert(err.message);
        }
        setLoading(false);
    };

    const handleAsk = async () => {
        if (!question.trim()) return;
        const userMsg = { type: "user", text: question };
        setMessages((prev) => [...prev, userMsg]);
        setQuestion("");
        setLoading(true);
        try {
            const res = await askRagQuestion(userMsg.text);
            setMessages((prev) => [
                ...prev,
                { type: "bot", text: res.answer, sources: res.sources || [] }
            ]);
        } catch (err) {
            alert(err.message);
        }
        setLoading(false);
    };

    return (
        <div className="rag-container">

            {/* ── Upload Bar ───────────────────────────────────── */}
            <div className="rag-upload-card">
                <div className="rag-upload-left">
                    <div className="rag-title">◈ Ask Your Report</div>
                    <div className="rag-subtitle">
                        Upload a PDF and query it with natural language
                    </div>
                </div>
                <div className="rag-upload-right">
                    <input
                        type="file"
                        accept=".pdf"
                        className="rag-file-input"
                        onChange={(e) => setFile(e.target.files[0])}
                    />
                    <button
                        className="rag-btn rag-btn-primary"
                        onClick={handleUpload}
                        disabled={loading}
                    >
                        Upload
                    </button>
                </div>
            </div>

            {/* ── Chat Box ────────────────────────────────────── */}
            <div className="rag-chat-box">

                {/* Header */}
                <div className="rag-chat-header">
                    <span className="rag-chat-header-title">Conversation</span>
                    <div className="rag-chat-status">
                        <span className="rag-status-dot" />
                        RAG Active
                    </div>
                </div>

                {/* Messages */}
                <div className="rag-messages">
                    {messages.length === 0 && !loading && (
                        <div className="rag-empty">
                            <div className="rag-empty-icon">📄</div>
                            <div className="rag-empty-title">No conversation yet</div>
                            <div className="rag-empty-sub">
                                Upload a PDF above and ask any question about its content
                            </div>
                        </div>
                    )}

                    {messages.map((msg, i) => (
                        <div key={i} className={`rag-msg-row rag-msg-row--${msg.type}`}>
                            <div className="rag-msg-label">
                                {msg.type === "user" ? "You" : "Assistant"}
                            </div>

                            {msg.type === "user" ? (
                                <div className="rag-msg-user">{msg.text}</div>
                            ) : (
                                <>
                                    <div className="rag-msg-bot">{msg.text}</div>
                                    {msg.sources && msg.sources.length > 0 && (
                                        <div className="rag-sources">
                                            <div className="rag-sources-label">
                                                Sources · {msg.sources.length} reference{msg.sources.length > 1 ? "s" : ""}
                                            </div>
                                            {msg.sources.map((s, idx) => (
                                                <div key={idx} className="rag-source-card">
                                                    <div className="rag-source-header">
                                                        <span className="rag-source-badge">pg {s.page}</span>
                                                    </div>
                                                    <p className="rag-source-text">
                                                        {s.text.slice(0, 220)}{s.text.length > 220 ? "…" : ""}
                                                    </p>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </>
                            )}
                        </div>
                    ))}

                    {loading && (
                        <div className="rag-msg-row rag-msg-row--bot">
                            <div className="rag-msg-label">Assistant</div>
                            <div className="rag-loading">
                                <div className="rag-loading-dots">
                                    <span /><span /><span />
                                </div>
                                <span className="rag-loading-text">Analysing document…</span>
                            </div>
                        </div>
                    )}

                    {/* Invisible anchor for auto-scrolling */}
                    <div ref={messagesEndRef} />
                </div>

                {/* Input — inside chat box, pinned to bottom */}
                <div className="rag-input-row">
                    <input
                        type="text"
                        className="rag-input"
                        placeholder="Ask a question about your document…"
                        value={question}
                        onChange={(e) => setQuestion(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && handleAsk()}
                    />
                    <button
                        className="rag-send-btn"
                        onClick={handleAsk}
                        disabled={loading}
                    >
                        <svg className="rag-send-icon" viewBox="0 0 24 24" fill="none"
                            stroke="currentColor" strokeWidth="2.2"
                            strokeLinecap="round" strokeLinejoin="round">
                            <line x1="22" y1="2" x2="11" y2="13" />
                            <polygon points="22 2 15 22 11 13 2 9 22 2" />
                        </svg>
                        Ask
                    </button>
                </div>

            </div>
        </div>
    );
}