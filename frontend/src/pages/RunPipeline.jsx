import { useState, useMemo, useEffect, useCallback, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { useSettings } from '../contexts/SettingsContext';
import { usePipeline } from '../contexts/PipelineContext';
import {
    HiOutlineLightningBolt,
    HiOutlineExternalLink,
    HiOutlineExclamationCircle,
    HiOutlineDownload,
    HiOutlineChevronDown,
    HiOutlineChevronUp,
    HiOutlineFilter,
    HiOutlineSortDescending,
    HiOutlineXCircle,
    HiOutlineChatAlt2,
    HiOutlinePaperAirplane,
    HiOutlineSparkles,
} from 'react-icons/hi';
import { generateReportPDF } from '../utils/pdfExport';
import ReportAssistant from '../components/ReportAssistant';
import './RunPipeline.css';



const SUGGESTIONS = ['Google', 'OpenAI', 'Microsoft', 'Anthropic', 'Meta AI', 'Tesla'];

const PIPELINE_STAGES = [
    'Guardrails', 'Searching', 'Scraping',
    'Validating', 'Filtering', 'Authority', 'Extracting',
    'Verifying', 'Scoring', 'Synthesizing'
];

/* ── Insight tag logic ─────────────────────────────────────────── */
function getCategoryTag(category) {
    if (!category) return 'capability';
    const lower = category.toLowerCase();
    if (lower.includes('security') || lower.includes('privacy')) return 'security';
    if (lower.includes('infra') || lower.includes('cloud')) return 'infrastructure';
    if (lower.includes('model') || lower.includes('llm') || lower.includes('ai')) return 'model';
    if (lower.includes('platform') || lower.includes('enterprise')) return 'platform';
    if (lower.includes('developer') || lower.includes('api') || lower.includes('sdk')) return 'developer';
    if (lower.includes('product') || lower.includes('feature')) return 'product';
    return 'capability';
}

/* ── Strategic Direction ────────────────────────────────────────── */
function deriveStrategicDirections(features) {
    if (!features?.length) return [];
    const allText = features.map(f =>
        `${f.title || ''} ${f.description || ''} ${f.category || ''}`
    ).join(' ').toLowerCase();

    const RULES = [
        { keywords: ['agent', 'autonomous', 'agentic'], label: 'Agentic Systems Expansion' },
        { keywords: ['llm', 'foundation model', 'training', 'fine-tun'], label: 'Foundation Model Investment' },
        { keywords: ['tpu', 'gpu', 'compute', 'scale', 'datacenter'], label: 'AI Infrastructure Scaling' },
        { keywords: ['multi-cloud', 'cross-cloud', 'hybrid cloud'], label: 'Cloud Consolidation Strategy' },
        { keywords: ['api', 'sdk', 'developer', 'toolkit', 'open source'], label: 'Developer Ecosystem Growth' },
        { keywords: ['security', 'privacy', 'compliance', 'zero trust'], label: 'Enterprise Security Hardening' },
        { keywords: ['enterprise', 'saas', 'b2b', 'workspace'], label: 'Enterprise Platform Strategy' },
        { keywords: ['launch', 'release', 'feature', 'product'], label: 'Product Innovation Push' },
        { keywords: ['edge', 'on-device', 'mobile', 'lightweight'], label: 'Edge AI Deployment' },
        { keywords: ['search', 'retrieval', 'rag', 'knowledge'], label: 'Knowledge System Expansion' },
        { keywords: ['video', 'image', 'multimodal', 'vision'], label: 'Multimodal AI Strategy' },
        { keywords: ['cost', 'pricing', 'free tier', 'affordable'], label: 'Market Accessibility Push' },
    ];

    return RULES.filter(rule =>
        rule.keywords.some(kw => allText.includes(kw))
    ).map(r => r.label).slice(0, 5);
}

/* ═══════════════════════════════════════════════════════════════════
   MAIN PAGE
   ═══════════════════════════════════════════════════════════════════ */
export default function RunPipeline() {
    const location = useLocation();
    const { settings } = useSettings();

    const {
        company, setCompany,
        loading,
        result,
        error,
        activeStage,
        elapsed,
        stageTimings,
        executePipeline,
        stopPipeline,
    } = usePipeline();

    // ── Local-only UI state ──────────────────────────────────────
    const [pdfLoading, setPdfLoading] = useState(false);
    const [sourcesExpanded, setSourcesExpanded] = useState(false);
    const [filterCategory, setFilterCategory] = useState('all');
    const [filterConfidence, setFilterConfidence] = useState('all');
    const [sortBy, setSortBy] = useState('confidence');
    const [expandedSignals, setExpandedSignals] = useState(new Set());

    const lastAutoRunCompanyRef = useRef('');
    const assistantRef = useRef(null);

    const toggleSignal = useCallback((idx) => {
        setExpandedSignals(prev => {
            const next = new Set(prev);
            if (next.has(idx)) next.delete(idx);
            else next.add(idx);
            return next;
        });
    }, []);

    const report = result?.report || result;

    const handleDownloadPDF = async () => {
        if (!report) return;
        setPdfLoading(true);
        try {
            await new Promise(r => setTimeout(r, 50));
            generateReportPDF(report, company);
        } finally {
            setPdfLoading(false);
        }
    };

    const handleRun = async (e) => {
        e.preventDefault();
        setExpandedSignals(new Set());
        setFilterCategory('all');
        setFilterConfidence('all');
        await executePipeline(company);
    };

    // Auto-run when navigated here from another page (e.g. Watchlist)
    useEffect(() => {
        const autoRunCompany = location.state?.autoRunCompany;
        if (!autoRunCompany || loading) return;
        if (lastAutoRunCompanyRef.current === autoRunCompany) return;
        lastAutoRunCompanyRef.current = autoRunCompany;
        setCompany(autoRunCompany);
        executePipeline(autoRunCompany);
    }, [location.state, executePipeline, loading, setCompany]);

    // ── Derived data ─────────────────────────────────────────────
    const allCategories = useMemo(() => {
        if (!report?.features?.length) return [];
        return [...new Set(report.features.map(f => f.category || 'General'))].sort();
    }, [report]);

    const distribution = useMemo(() => {
        if (!report?.features?.length) return [];
        const counts = {};
        report.features.forEach(f => {
            const cat = f.category || 'General';
            counts[cat] = (counts[cat] || 0) + 1;
        });
        return Object.entries(counts)
            .map(([cat, count]) => ({
                category: cat,
                count,
                pct: Math.round((count / report.features.length) * 100),
                tag: getCategoryTag(cat),
            }))
            .sort((a, b) => b.count - a.count);
    }, [report]);

    const filteredSignals = useMemo(() => {
        if (!report?.features?.length) return [];
        let signals = [...report.features];

        if (filterCategory !== 'all') {
            signals = signals.filter(f => (f.category || 'General') === filterCategory);
        }

        const threshold = settings.analysis.confidenceThreshold / 100;
        signals = signals.filter(f => {
            const score = f.confidence_score ?? f.confidence ?? 0;
            return score >= threshold;
        });

        if (filterConfidence !== 'all') {
            signals = signals.filter(f => {
                const score = f.confidence_score ?? f.confidence ?? 0;
                if (filterConfidence === 'high') return score >= 0.7;
                if (filterConfidence === 'mid') return score >= 0.4 && score < 0.7;
                if (filterConfidence === 'low') return score < 0.4;
                return true;
            });
        }

        if (sortBy === 'confidence') {
            signals.sort((a, b) => (b.confidence_score ?? b.confidence ?? 0) - (a.confidence_score ?? a.confidence ?? 0));
        } else if (sortBy === 'category') {
            signals.sort((a, b) => (a.category || '').localeCompare(b.category || ''));
        }

        return signals;
    }, [report, filterCategory, filterConfidence, sortBy, settings.analysis]);

    const avgConfidence = useMemo(() => {
        if (!report?.features?.length) return 0;
        const scores = report.features
            .map(f => f.confidence_score ?? f.confidence)
            .filter(s => s != null);
        return scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : 0;
    }, [report]);

    const strategicDirections = useMemo(() =>
        deriveStrategicDirections(report?.features), [report]);

    const hasResults = !!(result && report);

    return (
        /* Outer wrapper splits page into [main | sidebar] when results are shown */
        <div className="intelligence-page fade-in">

            {/* ══════════════════════════════════════════════════════
                MAIN COLUMN
            ══════════════════════════════════════════════════════ */}
            <div className="intel-main-col">

                {/* ── Header ─────────────────────────────────────── */}
                <div className="page-header">
                    <h1>Intelligence</h1>
                    <p>Analyze a company's competitive landscape — discover verified technical signals from the past {settings.analysis.timeWindow} days</p>
                </div>

                {/* ── Input Area ──────────────────────────────────── */}
                <form className="intel-input-section card" onSubmit={handleRun}>
                    <div className="intel-input-row">
                        <div className="intel-input-wrapper">
                            <HiOutlineLightningBolt className="intel-input-icon" />
                            <input
                                type="text"
                                className="input intel-input"
                                placeholder="Enter a company name to analyze..."
                                value={company}
                                onChange={e => setCompany(e.target.value)}
                                disabled={loading}
                                maxLength={200}
                            />
                        </div>
                        <button
                            type="submit"
                            className="btn btn-primary btn-lg intel-run-btn"
                            disabled={loading || !company.trim()}
                        >
                            {loading ? (
                                <><span className="spinner" /> Analyzing...</>
                            ) : (
                                <><HiOutlineLightningBolt /> Analyze</>
                            )}
                        </button>
                        {loading && (
                            <button
                                type="button"
                                className="btn btn-danger btn-lg intel-stop-btn"
                                onClick={stopPipeline}
                            >
                                <HiOutlineXCircle /> Stop
                            </button>
                        )}
                    </div>

                    <div className="intel-suggestions">
                        {SUGGESTIONS.map(s => (
                            <button
                                key={s}
                                type="button"
                                className="suggestion-chip"
                                onClick={() => setCompany(s)}
                                disabled={loading}
                            >
                                {s}
                            </button>
                        ))}
                    </div>
                </form>

                {/* ── Pipeline Animation ──────────────────────────── */}
                {loading && (
                    <PipelineAnimation
                        company={company}
                        activeStage={activeStage}
                        elapsed={elapsed}
                        stageTimings={stageTimings}
                    />
                )}

                {/* ── Error ──────────────────────────────────────── */}
                {error && (
                    <div className="card error-section fade-in">
                        <HiOutlineExclamationCircle className="error-icon" />
                        <div>
                            <h3>Analysis Failed</h3>
                            <p>{error}</p>
                        </div>
                    </div>
                )}

                {/* ── Results ────────────────────────────────────── */}
                {hasResults && (
                    <div className="results-section fade-in-up">

                        <div className="card result-header-card">
                            <div className="result-header-row">
                                <div className="result-meta">
                                    <h2>{report.company_name || company}</h2>
                                    <div className="result-badges">
                                        <span className="badge badge-accent">{report.total_features_verified || report.features?.length || 0} Signals</span>
                                        <span className="badge badge-info">{report.total_sources_analysed || 0} Sources</span>
                                        {distribution.length > 0 && <span className="badge badge-purple">{distribution.length} Themes</span>}
                                        {report.generated_at && (
                                            <span className="badge badge-warning">{new Date(report.generated_at).toLocaleDateString()}</span>
                                        )}
                                    </div>
                                </div>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                    <button
                                        className="btn btn-pdf"
                                        onClick={handleDownloadPDF}
                                        disabled={pdfLoading || loading}
                                        title="Download report as PDF"
                                        id="download-pdf-btn"
                                    >
                                        {pdfLoading ? (
                                            <><span className="spinner spinner-sm" /> Generating…</>
                                        ) : (
                                            <><HiOutlineDownload /> Download PDF</>
                                        )}
                                    </button>
                                    <button
                                        className="btn btn-primary"
                                        onClick={() => {
                                            assistantRef.current?.triggerIndex();
                                        }}
                                        disabled={loading}
                                    >
                                        <HiOutlineSparkles /> Ask Report Assistant
                                    </button>
                                </div>
                            </div>
                        </div>

                        {(report.executive_summary || distribution.length > 0) && (
                            <div className="insight-grid fade-in-up">
                                {report.executive_summary && (
                                    <div className="card card-accent executive-card">
                                        <div className="executive-label">Executive Insight</div>
                                        <p className="executive-text">{report.executive_summary}</p>
                                        <div className="executive-stats">
                                            <div className="exec-stat">
                                                <span className="exec-stat-value">{report.features?.length || 0}</span>
                                                <span className="exec-stat-label">Signals</span>
                                            </div>
                                            <div className="exec-stat">
                                                <span className="exec-stat-value">{report.total_sources_analysed || 0}</span>
                                                <span className="exec-stat-label">Sources</span>
                                            </div>
                                            <div className="exec-stat">
                                                <span className={`exec-stat-value ${avgConfidence >= 0.7 ? 'text-success' : avgConfidence >= 0.4 ? 'text-warning' : 'text-error'}`}>
                                                    {(avgConfidence * 100).toFixed(0)}%
                                                </span>
                                                <span className="exec-stat-label">Avg Confidence</span>
                                            </div>
                                        </div>
                                        {strategicDirections.length > 0 && (
                                            <div className="strategic-directions">
                                                <span className="strategic-label">Strategic Direction</span>
                                                <div className="strategic-tags">
                                                    {strategicDirections.map((d, i) => (
                                                        <span key={i} className="strategic-tag">{d}</span>
                                                    ))}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                )}

                                {distribution.length > 0 && (
                                    <div className="card distribution-card">
                                        <div className="distribution-label">Signal Distribution</div>
                                        <div className="distribution-bars">
                                            {distribution.map((d, i) => (
                                                <div key={i} className="dist-row">
                                                    <span className={`dist-cat insight-tag ${d.tag}`}>{d.category}</span>
                                                    <div className="dist-bar-track">
                                                        <div
                                                            className={`dist-bar-fill tag-${d.tag}`}
                                                            style={{ width: `${d.pct}%` }}
                                                        />
                                                    </div>
                                                    <span className="dist-count">{d.count}</span>
                                                </div>
                                            ))}
                                        </div>
                                        <div className="dist-confidence">
                                            <div className="dist-conf-header">
                                                <span className="dist-conf-label">Avg Confidence</span>
                                                <span className={`dist-conf-value ${avgConfidence >= 0.7 ? 'high' : avgConfidence >= 0.4 ? 'mid' : 'low'}`}>
                                                    {(avgConfidence * 100).toFixed(0)}%
                                                </span>
                                            </div>
                                            <div className="dist-conf-track">
                                                <div
                                                    className={`dist-conf-fill ${avgConfidence >= 0.7 ? 'high' : avgConfidence >= 0.4 ? 'mid' : 'low'}`}
                                                    style={{ width: `${(avgConfidence * 100).toFixed(0)}%` }}
                                                />
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}

                        {report.features?.length > 0 && (
                            <div className="filter-bar fade-in-up">
                                <div className="filter-controls">
                                    <div className="filter-group">
                                        <HiOutlineFilter className="filter-icon" />
                                        <select
                                            className="filter-select"
                                            value={filterCategory}
                                            onChange={e => setFilterCategory(e.target.value)}
                                        >
                                            <option value="all">All Themes</option>
                                            {allCategories.map(c => (
                                                <option key={c} value={c}>{c}</option>
                                            ))}
                                        </select>
                                    </div>
                                    <div className="filter-group">
                                        <select
                                            className="filter-select"
                                            value={filterConfidence}
                                            onChange={e => setFilterConfidence(e.target.value)}
                                        >
                                            <option value="all">All Confidence</option>
                                            <option value="high">High (≥70%)</option>
                                            <option value="mid">Medium (40-69%)</option>
                                            <option value="low">Low (&lt;40%)</option>
                                        </select>
                                    </div>
                                    <div className="filter-group">
                                        <HiOutlineSortDescending className="filter-icon" />
                                        <select
                                            className="filter-select"
                                            value={sortBy}
                                            onChange={e => setSortBy(e.target.value)}
                                        >
                                            <option value="confidence">Sort: Confidence ↓</option>
                                            <option value="category">Sort: Category</option>
                                        </select>
                                    </div>
                                </div>
                                <span className="filter-count">
                                    Showing {filteredSignals.length} of {report.features.length} signals
                                </span>
                            </div>
                        )}

                        {filteredSignals.length > 0 && (
                            <div className="signals-section">
                                <div className="signals-list stagger">
                                    {filteredSignals.map((f, i) => (
                                        <SignalCard
                                            key={`${f.title}-${i}`}
                                            signal={f}
                                            index={i}
                                            isExpanded={expandedSignals.has(i)}
                                            onToggle={() => toggleSignal(i)}
                                        />
                                    ))}
                                </div>
                            </div>
                        )}

                        {filteredSignals.length === 0 && report.features?.length > 0 && (
                            <div className="card empty-state">
                                <div className="icon">🔍</div>
                                <h3>No signals match your filters</h3>
                                <p>Try adjusting the category or confidence filters above.</p>
                            </div>
                        )}

                        {report.all_sources && report.all_sources.length > 0 && (
                            <div className="card evidence-section fade-in-up">
                                <button
                                    className="evidence-toggle"
                                    onClick={() => setSourcesExpanded(!sourcesExpanded)}
                                >
                                    <span>
                                        Evidence Layer
                                        <span className="evidence-count">{report.all_sources.length} sources</span>
                                    </span>
                                    {sourcesExpanded ? <HiOutlineChevronUp /> : <HiOutlineChevronDown />}
                                </button>
                                {sourcesExpanded && (
                                    <div className="evidence-list fade-in">
                                        {report.all_sources.map((url, i) => (
                                            <a
                                                key={i}
                                                href={url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="evidence-item"
                                            >
                                                <HiOutlineExternalLink className="evidence-link-icon" />
                                                <span>{url.length > 90 ? url.slice(0, 90) + '...' : url}</span>
                                            </a>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Report Assistant RAG UI */}
                        <div>
                            <ReportAssistant report={report} ref={assistantRef} />
                        </div>

                    </div>
                )}
            </div>
        </div>
    );
}

/* ── Signal Card ────────────────────────────────────────────────── */
function SignalCard({ signal: f, index, isExpanded, onToggle }) {
    const score = f.confidence_score ?? f.confidence;
    const pct = score != null ? Math.round(score * 100) : null;
    const level = score >= 0.7 ? 'high' : score >= 0.4 ? 'mid' : 'low';
    const tag = getCategoryTag(f.category);

    return (
        <div className={`signal-card ${isExpanded ? 'expanded' : ''} fade-in-up`}>
            <div className="signal-header" onClick={onToggle}>
                <div className="signal-rank">{f.rank || index + 1}</div>
                <div className="signal-title-area">
                    <h4>{f.title || f.feature_title || 'Untitled Signal'}</h4>
                </div>
                <span className={`insight-tag ${tag}`}>{f.category || 'General'}</span>
                {pct != null && (
                    <div className="confidence-bar">
                        <div className="confidence-bar-track">
                            <div
                                className={`confidence-bar-fill ${level}`}
                                style={{ width: `${pct}%` }}
                            />
                        </div>
                        <span className={`confidence-label ${level}`}>{pct}%</span>
                    </div>
                )}
                <button className="signal-toggle-btn" onClick={(e) => { e.stopPropagation(); onToggle(); }}>
                    {isExpanded ? <HiOutlineChevronUp /> : <HiOutlineChevronDown />}
                </button>
            </div>

            {isExpanded && (
                <div className="signal-expanded fade-in">
                    {(f.description || f.feature_summary) && (
                        <p className="signal-description">
                            {f.description || f.feature_summary}
                        </p>
                    )}
                    {f.impact_assessment && (
                        <div className="signal-impact">
                            <span className="impact-label">Impact</span>
                            <span className="impact-text">{f.impact_assessment}</span>
                        </div>
                    )}
                    <div className="signal-footer">
                        {f.key_metrics && f.key_metrics.length > 0 && (
                            <div className="signal-metrics">
                                {f.key_metrics.map((m, j) => (
                                    <span key={j} className="metric-chip">{m}</span>
                                ))}
                            </div>
                        )}
                        {f.source_count && (
                            <span className="signal-meta">{f.source_count} source{f.source_count > 1 ? 's' : ''}</span>
                        )}
                        {f.source_url && (
                            <a
                                href={f.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="signal-source-link"
                            >
                                <HiOutlineExternalLink /> Source
                            </a>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

/* ── Pipeline Animation ─────────────────────────────────────────── */
function PipelineAnimation({ company, activeStage, elapsed, stageTimings }) {
    const formatTime = (s) => {
        const m = Math.floor(s / 60);
        const sec = s % 60;
        return `${m}:${sec.toString().padStart(2, '0')}`;
    };

    const progress = ((activeStage + 1) / PIPELINE_STAGES.length) * 100;

    return (
        <div className="card pipeline-anim-card fade-in">
            <div className="pipeline-anim-header">
                <div>
                    <h3>Analyzing <strong>{company}</strong></h3>
                    <p className="pipeline-anim-stage">
                        Stage {activeStage + 1} of {PIPELINE_STAGES.length} — <span className="pipeline-active-name">{PIPELINE_STAGES[activeStage]}</span>
                    </p>
                </div>
                <div className="pipeline-anim-timer">
                    <span className="timer-value">{formatTime(elapsed)}</span>
                    <span className="timer-label">Elapsed</span>
                </div>
            </div>

            <div className="pipeline-flow">
                {PIPELINE_STAGES.map((stage, i) => {
                    const state = i < activeStage ? 'done' : i === activeStage ? 'active' : 'pending';
                    
                    // Calculate duration for this stage
                    let durationText = '';
                    if (stageTimings && stageTimings[i]) {
                        const t = stageTimings[i];
                        if (t.end && t.start) {
                            durationText = `${Math.round((t.end - t.start) / 1000)}s`;
                        } else if (t.start) {
                            durationText = `${Math.round((Date.now() - t.start) / 1000)}s`;
                        }
                    }

                    return (
                        <div key={i} className="pipeline-flow-item">
                            <div className={`flow-node ${state}`}>
                                {state === 'done' ? (
                                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                                        <path d="M2 6L5 9L10 3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                                    </svg>
                                ) : (
                                    <span className="flow-node-num">{i + 1}</span>
                                )}
                            </div>
                            <span className={`flow-label ${state}`}>
                                {stage}
                                {durationText && <span className="stage-duration"> {durationText}</span>}
                            </span>
                            {i < PIPELINE_STAGES.length - 1 && (
                                <div className={`flow-connector ${i < activeStage ? 'done' : ''}`} />
                            )}
                        </div>
                    );
                })}
            </div>

            <div className="pipeline-anim-bar">
                <div className="pipeline-anim-bar-fill" style={{ width: `${progress}%` }} />
            </div>
        </div>
    );
}