import { useState, useMemo, useEffect } from 'react';
import {
    HiOutlineChartBar,
    HiOutlinePlusCircle,
    HiOutlineX,
    HiOutlineTrendingUp,
    HiOutlineTrendingDown,
    HiOutlineArrowRight,
    HiOutlineLightningBolt,
    HiOutlineEye,
    HiOutlineClock,
    HiOutlineSwitchHorizontal,
} from 'react-icons/hi';
import { getCompetitors, getReports } from '../api';
import { useSettings } from '../contexts/SettingsContext';
import { formatDateTime } from '../utils/formatDate';
import {
    Chart as ChartJS,
    RadialLinearScale,
    PointElement,
    LineElement,
    Filler,
    Tooltip,
    Legend,
    CategoryScale,
    LinearScale,
    BarElement,
} from 'chart.js';
import { Radar, Bar } from 'react-chartjs-2';
import './Analysis.css';

ChartJS.register(
    RadialLinearScale, PointElement, LineElement, Filler,
    Tooltip, Legend, CategoryScale, LinearScale, BarElement
);

const MAX_ITEMS = 3;
const COLORS = ['var(--accent-primary)', 'var(--info)', 'var(--purple)'];
const COLOR_HEX = ['#4ade80', '#60a5fa', '#a78bfa'];

/* ── Strategic Direction ───────────────────────────────────────── */
function deriveDirections(features) {
    if (!features?.length) return [];
    const text = features.map(f =>
        `${f.feature_title || ''} ${f.description || ''} ${f.category || ''}`
    ).join(' ').toLowerCase();

    const RULES = [
        { keywords: ['agent', 'autonomous', 'agentic'],       label: 'Agentic Systems' },
        { keywords: ['llm', 'foundation model', 'training'],  label: 'Foundation Models' },
        { keywords: ['tpu', 'gpu', 'compute', 'scale'],       label: 'AI Infrastructure' },
        { keywords: ['multi-cloud', 'cross-cloud', 'hybrid'], label: 'Cloud Consolidation' },
        { keywords: ['api', 'sdk', 'developer', 'toolkit'],   label: 'Developer Ecosystem' },
        { keywords: ['security', 'privacy', 'compliance'],    label: 'Security Focus' },
        { keywords: ['enterprise', 'saas', 'b2b', 'workspace'], label: 'Enterprise Strategy' },
        { keywords: ['launch', 'release', 'product'],         label: 'Product Innovation' },
        { keywords: ['edge', 'on-device', 'mobile'],          label: 'Edge AI' },
        { keywords: ['search', 'retrieval', 'rag'],            label: 'Knowledge Systems' },
        { keywords: ['video', 'image', 'multimodal', 'vision'], label: 'Multimodal AI' },
        { keywords: ['cost', 'pricing', 'free tier'],          label: 'Market Accessibility' },
    ];

    return RULES.filter(r => r.keywords.some(kw => text.includes(kw)))
        .map(r => r.label).slice(0, 4);
}

/* ── Helpers ────────────────────────────────────────────────────── */
function getAvgConf(features) {
    if (!features?.length) return 0;
    const scores = features.map(f => f.confidence_score).filter(s => s != null);
    return scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : 0;
}

function getCategoryDist(features) {
    if (!features?.length) return {};
    const counts = {};
    features.forEach(f => { const cat = f.category || 'General'; counts[cat] = (counts[cat] || 0) + 1; });
    return counts;
}

function getTopFeatures(features, limit = 4) {
    if (!features?.length) return [];
    return [...features]
        .sort((a, b) => {
            const impOrder = { high: 3, medium: 2, low: 1 };
            const diff = (impOrder[b.importance] || 1) - (impOrder[a.importance] || 1);
            return diff !== 0 ? diff : (b.confidence_score || 0) - (a.confidence_score || 0);
        })
        .slice(0, limit);
}

function buildComparativeSummary(items) {
    if (items.length < 2) return '';
    const parts = items.map(c => {
        const dirs = deriveDirections(c.features);
        const topCat = Object.entries(getCategoryDist(c.features)).sort((a, b) => b[1] - a[1])[0];
        const focus = dirs.length > 0 ? dirs[0].toLowerCase() : (topCat ? topCat[0].toLowerCase() : 'general technology');
        return { name: c.label, focus, signals: c.features?.length || 0 };
    });
    let summary = parts.map(s => `${s.name} focuses on ${s.focus}`).join(', while ') + '. ';
    const sorted = [...parts].sort((a, b) => b.signals - a.signals);
    if (sorted[0].signals > sorted[sorted.length - 1].signals * 1.3) {
        summary += `${sorted[0].name} shows stronger signal activity with ${sorted[0].signals} verified signals.`;
    }
    return summary;
}

function deriveKeyDifferences(items) {
    const diffs = [];
    if (items.length < 2) return diffs;
    items.forEach(c => {
        const top = getTopFeatures(c.features, 1)[0];
        if (top) {
            const impact = top.impact_assessment || top.evidence || '';
            diffs.push(`${c.label}: "${top.feature_title || top.feature_text}"${impact ? ` — ${impact}` : ''}`);
        }
    });
    const cats = items.map(c => {
        const dist = getCategoryDist(c.features);
        const topCat = Object.entries(dist).sort((a, b) => b[1] - a[1])[0];
        return { name: c.label, topCat: topCat?.[0] || 'General', count: topCat?.[1] || 0 };
    });
    if (cats[0]?.topCat !== cats[1]?.topCat) {
        diffs.push(`${cats[0].name} leads in ${cats[0].topCat} (${cats[0].count} signals), while ${cats[1].name} focuses on ${cats[1].topCat} (${cats[1].count} signals).`);
    }
    const byConf = [...items].sort((a, b) => getAvgConf(b.features) - getAvgConf(a.features));
    const topConf = getAvgConf(byConf[0].features);
    const lowConf = getAvgConf(byConf[byConf.length - 1].features);
    if (topConf > 0 && topConf - lowConf > 0.1) {
        diffs.push(`${byConf[0].name} shows higher confidence (${(topConf * 100).toFixed(0)}%) vs ${byConf[byConf.length - 1].name} (${(lowConf * 100).toFixed(0)}%).`);
    }
    return diffs.slice(0, 6);
}

function getCategoryOverlap(items) {
    if (items.length < 2) return { shared: [], unique: {} };
    const catSets = items.map(c => new Set(Object.keys(getCategoryDist(c.features))));
    const allCats = new Set(catSets.flatMap(s => [...s]));
    const shared = [...allCats].filter(cat => catSets.every(s => s.has(cat)));
    const unique = {};
    items.forEach((c, i) => {
        unique[c.label] = [...catSets[i]].filter(cat => !catSets.some((s, j) => j !== i && s.has(cat)));
    });
    return { shared, unique };
}

function formatDate(dateStr) {
    return formatDateTime(dateStr);
}


export default function Analysis() {
    // Mode: 'companies' or 'timeline'
    const [mode, setMode] = useState('companies');

    // Company mode state
    const [available, setAvailable] = useState([]);
    const [reportCounts, setReportCounts] = useState({});
    const [selectedCompanies, setSelectedCompanies] = useState([]);
    const [loadingList, setLoadingList] = useState(true);

    // Timeline mode state
    const [timelineCompany, setTimelineCompany] = useState('');
    const [allReports, setAllReports] = useState([]);
    const [selectedReports, setSelectedReports] = useState([]);
    const [loadingReports, setLoadingReports] = useState(false);

    // Shared
    const [comparisonData, setComparisonData] = useState([]);
    const [loading, setLoading] = useState(false);

    // Load available companies
    useEffect(() => {
        (async () => {
            setLoadingList(true);
            try { 
                const comps = await getCompetitors();
                setAvailable(comps);
                const counts = {};
                await Promise.all(comps.map(async (c) => {
                    try {
                        const reps = await getReports(c.name);
                        counts[c.name] = Array.isArray(reps) ? reps.length : 1;
                    } catch {
                        counts[c.name] = 0;
                    }
                }));
                setReportCounts(counts);
            }
            catch { setAvailable([]); }
            finally { setLoadingList(false); }
        })();
    }, []);

    // Reset on mode change
    useEffect(() => {
        setComparisonData([]);
        setSelectedCompanies([]);
        setSelectedReports([]);
        setTimelineCompany('');
        setAllReports([]);
    }, [mode]);

    // COMPANY MODE: Fetch latest report per company
    useEffect(() => {
        if (mode !== 'companies' || selectedCompanies.length < 2) { setComparisonData([]); return; }
        let cancelled = false;
        setLoading(true);
        (async () => {
            const results = [];
            for (const name of selectedCompanies) {
                try {
                    const reports = await getReports(name);
                    const arr = Array.isArray(reports) ? reports : [reports];
                    const latest = arr[0];
                    results.push({
                        label: name,
                        features: latest?.features || [],
                        summary: latest?.executive_summary || '',
                        sources: latest?.total_sources || 0,
                    });
                } catch {
                    results.push({ label: name, features: [], summary: '', sources: 0 });
                }
            }
            if (!cancelled) { setComparisonData(results); setLoading(false); }
        })();
        return () => { cancelled = true; };
    }, [selectedCompanies, mode]);

    // TIMELINE MODE: Load all reports when company is selected
    useEffect(() => {
        if (mode !== 'timeline' || !timelineCompany) { setAllReports([]); return; }
        let cancelled = false;
        setLoadingReports(true);
        (async () => {
            try {
                const reports = await getReports(timelineCompany);
                const arr = Array.isArray(reports) ? reports : [reports];
                if (!cancelled) setAllReports(arr);
            } catch { if (!cancelled) setAllReports([]); }
            finally { if (!cancelled) setLoadingReports(false); }
        })();
        return () => { cancelled = true; };
    }, [timelineCompany, mode]);

    // TIMELINE MODE: Build comparison data from selected reports
    useEffect(() => {
        if (mode !== 'timeline' || selectedReports.length < 2) { setComparisonData([]); return; }
        const results = selectedReports.map(r => ({
            label: `${timelineCompany} (${formatDate(r.created_at)})`,
            features: r.features || [],
            summary: r.executive_summary || '',
            sources: r.total_sources || 0,
        }));
        setComparisonData(results);
    }, [selectedReports, mode, timelineCompany]);

    // Company mode helpers
    function addCompany(name) {
        if (selectedCompanies.length >= MAX_ITEMS || selectedCompanies.includes(name)) return;
        setSelectedCompanies(prev => [...prev, name]);
    }
    function removeCompany(name) {
        setSelectedCompanies(prev => prev.filter(n => n !== name));
    }

    // Timeline mode helpers
    function toggleReport(report) {
        setSelectedReports(prev => {
            const exists = prev.find(r => r.id === report.id);
            if (exists) return prev.filter(r => r.id !== report.id);
            if (prev.length >= MAX_ITEMS) return prev;
            return [...prev, report];
        });
    }

    // Derived data
    const comparativeSummary = useMemo(() => buildComparativeSummary(comparisonData), [comparisonData]);
    const keyDifferences = useMemo(() => deriveKeyDifferences(comparisonData), [comparisonData]);
    const categoryOverlap = useMemo(() => getCategoryOverlap(comparisonData), [comparisonData]);
    const hasResults = !loading && comparisonData.length >= 2;

    return (
        <div className="analysis-page fade-in">
            <div className="page-header">
                <h1>Analysis</h1>
                <p>Compare competitive intelligence across companies or track a single company over time</p>
            </div>

            <div className="card analysis-hero-strip fade-in-up">
                <div className="analysis-hero-item">
                    <span>Mode</span>
                    <strong>{mode === 'companies' ? 'Company Compare' : 'Timeline Compare'}</strong>
                </div>
                <div className="analysis-hero-item">
                    <span>Selection</span>
                    <strong>{mode === 'companies' ? `${selectedCompanies.length}/${MAX_ITEMS} companies` : `${selectedReports.length}/${MAX_ITEMS} reports`}</strong>
                </div>
                <div className="analysis-hero-item">
                    <span>Status</span>
                    <strong>{loading ? 'Analyzing...' : hasResults ? `${comparisonData.length} sets ready` : 'Awaiting selection'}</strong>
                </div>
            </div>

            {/* ── Mode Toggle ────────────────────────────────── */}
            <div className="mode-toggle">
                <button
                    className={`mode-btn ${mode === 'companies' ? 'active' : ''}`}
                    onClick={() => setMode('companies')}
                >
                    <HiOutlineSwitchHorizontal /> Compare Companies
                </button>
                <button
                    className={`mode-btn ${mode === 'timeline' ? 'active' : ''}`}
                    onClick={() => setMode('timeline')}
                >
                    <HiOutlineClock /> Compare Timeline
                </button>
            </div>

            {/* ═══════════════════════════════════════════════════
                COMPANY MODE SELECTOR
                ═══════════════════════════════════════════════════ */}
            {mode === 'companies' && (
                <div className="card analysis-selector">
                    <div className="selector-header">
                        <h3>Select Companies to Compare</h3>
                        <span className="selector-count">{selectedCompanies.length} / {MAX_ITEMS}</span>
                    </div>
                    {selectedCompanies.length > 0 && (
                        <div className="selected-chips">
                            {selectedCompanies.map((name, i) => (
                                <span key={name} className="selected-chip" style={{ borderColor: COLORS[i] }}>
                                    <span className="chip-dot" style={{ background: COLORS[i] }} />
                                    {name}
                                    <button className="chip-remove" onClick={() => removeCompany(name)}><HiOutlineX /></button>
                                </span>
                            ))}
                        </div>
                    )}
                    {loadingList ? (
                        <div style={{ padding: '16px 0', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                            <span className="spinner" style={{ marginRight: '8px' }} /> Loading...
                        </div>
                    ) : available.length === 0 ? (
                        <p className="selector-empty">No companies tracked yet. Run the intelligence pipeline first.</p>
                    ) : (
                        <div className="available-companies">
                            {available.filter(c => !selectedCompanies.includes(c.name)).map(c => (
                                <button key={c.id} className="available-chip" onClick={() => addCompany(c.name)}
                                    disabled={selectedCompanies.length >= MAX_ITEMS}>
                                    <HiOutlinePlusCircle /> {c.name}
                                </button>
                            ))}
                        </div>
                    )}
                    {selectedCompanies.length === 1 && (
                        <p className="selector-hint">Select at least 2 companies to start analysis.</p>
                    )}
                </div>
            )}

            {/* ═══════════════════════════════════════════════════
                TIMELINE MODE SELECTOR
                ═══════════════════════════════════════════════════ */}
            {mode === 'timeline' && (
                <div className="card analysis-selector">
                    <div className="selector-header">
                        <h3>Select Company & Reports to Compare</h3>
                        <span className="selector-count">{selectedReports.length} / {MAX_ITEMS} reports</span>
                    </div>

                    {/* Company picker */}
                    {loadingList ? (
                        <div style={{ padding: '16px 0', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                            <span className="spinner" style={{ marginRight: '8px' }} /> Loading...
                        </div>
                    ) : (
                        <div className="timeline-company-select">
                            <span className="timeline-label">Company</span>
                            {available.filter(c => reportCounts[c.name] >= 2).length === 0 ? (
                                <p className="selector-hint" style={{ marginTop: 0 }}>
                                    No companies have a timeline of reports yet. Run the pipeline multiple times for the same company to build a timeline.
                                </p>
                            ) : (
                                <div className="available-companies">
                                    {available.filter(c => reportCounts[c.name] >= 2).map(c => (
                                        <button
                                            key={c.id}
                                            className={`available-chip ${timelineCompany === c.name ? 'selected' : ''}`}
                                            onClick={() => { setTimelineCompany(c.name); setSelectedReports([]); }}
                                        >
                                            {c.name}
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Report date picker */}
                    {timelineCompany && (
                        <div className="timeline-reports-select">
                            <span className="timeline-label">Select Reports to Compare</span>
                            {loadingReports ? (
                                <div style={{ padding: '12px 0', color: 'var(--text-muted)', fontSize: '0.84rem' }}>
                                    <span className="spinner" style={{ marginRight: '8px' }} /> Loading reports...
                                </div>
                            ) : allReports.length === 0 ? (
                                <p className="selector-empty">No reports found for {timelineCompany}.</p>
                            ) : allReports.length < 2 ? (
                                <p className="selector-hint">Only 1 report available. Run the pipeline again on a different day to compare.</p>
                            ) : (
                                <div className="timeline-report-chips">
                                    {allReports.map((r) => {
                                        const isSelected = selectedReports.find(sr => sr.id === r.id);
                                        const idx = selectedReports.findIndex(sr => sr.id === r.id);
                                        return (
                                            <button
                                                key={r.id}
                                                className={`timeline-chip ${isSelected ? 'selected' : ''}`}
                                                onClick={() => toggleReport(r)}
                                                disabled={!isSelected && selectedReports.length >= MAX_ITEMS}
                                                style={isSelected ? { borderColor: COLORS[idx] } : {}}
                                            >
                                                {isSelected && <span className="chip-dot" style={{ background: COLORS[idx] }} />}
                                                <span className="tc-date">{formatDate(r.created_at)}</span>
                                                <span className="tc-meta">{r.total_features || 0} signals · {r.total_sources || 0} sources</span>
                                            </button>
                                        );
                                    })}
                                </div>
                            )}
                        </div>
                    )}

                    {selectedReports.length === 1 && (
                        <p className="selector-hint">Select at least 2 reports to compare.</p>
                    )}
                </div>
            )}

            {/* ── Loading ─────────────────────────────────────── */}
            {loading && (
                <div className="card analysis-loading-card">
                    <div className="spinner spinner-lg analysis-loading-spinner" />
                    <p>Loading intelligence data...</p>
                </div>
            )}

            {/* ═══════════════════════════════════════════════════
                COMPARISON RESULTS (shared between both modes)
                ═══════════════════════════════════════════════════ */}
            {hasResults && (
                <div className="analysis-results stagger">

                    {/* 1. Executive Summary Comparison */}
                    <div className="card card-accent comp-summary-card fade-in-up">
                        <div className="comp-summary-label">
                            {mode === 'timeline' ? 'Timeline Intelligence' : 'Comparative Intelligence'}
                        </div>
                        <p className="comp-summary-headline">{comparativeSummary}</p>
                        <div className="exec-comparison">
                            {comparisonData.map((c, i) => (
                                <div key={c.label} className="exec-block">
                                    <div className="exec-block-header">
                                        <span className="exec-dot" style={{ background: COLORS[i] }} />
                                        <span className="exec-company-name">{c.label}</span>
                                    </div>
                                    <p className="exec-block-text">
                                        {c.summary || 'No executive summary available.'}
                                    </p>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* 2. Strategic Direction */}
                    <div className="card comp-direction-card fade-in-up">
                        <h3 className="comp-section-title">Strategic Direction</h3>
                        <div className="direction-grid">
                            {comparisonData.map((c, i) => {
                                const dirs = deriveDirections(c.features);
                                return (
                                    <div key={c.label} className="direction-column">
                                        <div className="direction-company">
                                            <span className="direction-dot" style={{ background: COLORS[i] }} />
                                            <span>{c.label}</span>
                                        </div>
                                        <div className="direction-tags">
                                            {dirs.length > 0 ? dirs.map((d, j) => (
                                                <span key={j} className="direction-tag">{d}</span>
                                            )) : <span className="direction-tag empty">No clear direction</span>}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>

                    {/* 3. Category Coverage */}
                    {(categoryOverlap.shared.length > 0 || Object.values(categoryOverlap.unique).some(u => u.length > 0)) && (
                        <div className="card comp-overlap-card fade-in-up">
                            <h3 className="comp-section-title"><HiOutlineEye /> Category Coverage</h3>
                            <div className="overlap-layout">
                                {categoryOverlap.shared.length > 0 && (
                                    <div className="overlap-section">
                                        <span className="overlap-label shared">{mode === 'timeline' ? 'Consistent Focus' : 'Shared Focus Areas'}</span>
                                        <div className="overlap-tags">
                                            {categoryOverlap.shared.map(cat => <span key={cat} className="overlap-tag shared">{cat}</span>)}
                                        </div>
                                    </div>
                                )}
                                {comparisonData.map((c, i) => {
                                    const uniqueCats = categoryOverlap.unique[c.label] || [];
                                    if (uniqueCats.length === 0) return null;
                                    return (
                                        <div key={c.label} className="overlap-section">
                                            <span className="overlap-label" style={{ color: COLORS[i] }}>
                                                {mode === 'timeline' ? `New in ${c.label}` : `Only ${c.label}`}
                                            </span>
                                            <div className="overlap-tags">
                                                {uniqueCats.map(cat => <span key={cat} className="overlap-tag unique" style={{ borderColor: COLOR_HEX[i] + '40', color: COLOR_HEX[i] }}>{cat}</span>)}
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}

                    {/* 4. Top Signals Compared */}
                    <div className="card comp-signals-card fade-in-up">
                        <h3 className="comp-section-title"><HiOutlineLightningBolt /> Top Signals Compared</h3>
                        <div className="signals-comparison">
                            {comparisonData.map((c, i) => {
                                const topFeats = getTopFeatures(c.features, 4);
                                return (
                                    <div key={c.label} className="signals-column">
                                        <div className="signals-col-header">
                                            <span className="signals-col-dot" style={{ background: COLORS[i] }} />
                                            <span>{c.label}</span>
                                            <span className="signals-col-count">{c.features.length} signals</span>
                                        </div>
                                        <div className="signals-col-list">
                                            {topFeats.map((f, j) => (
                                                <div key={j} className="signal-compare-item">
                                                    <div className="sci-header">
                                                        <span className="sci-title">{f.feature_title || f.feature_text}</span>
                                                        {f.importance && <span className={`sci-importance ${f.importance}`}>{f.importance}</span>}
                                                    </div>
                                                    {(f.description || f.feature_text) && (
                                                        <p className="sci-desc">
                                                            {(f.description || f.feature_text || '').slice(0, 120)}
                                                            {(f.description || '').length > 120 ? '…' : ''}
                                                        </p>
                                                    )}
                                                    {(f.impact_assessment || f.evidence) && (
                                                        <div className="sci-impact">
                                                            <span className="sci-impact-label">Impact</span>
                                                            <span>{f.impact_assessment || f.evidence}</span>
                                                        </div>
                                                    )}
                                                    <div className="sci-meta">
                                                        <span className="sci-category">{f.category}</span>
                                                        <span className="sci-conf">{Math.round((f.confidence_score || 0) * 100)}%</span>
                                                    </div>
                                                </div>
                                            ))}
                                            {topFeats.length === 0 && <p className="signals-col-empty">No signals available</p>}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>

                    {/* 5. Signal Metrics */}
                    <div className="card comp-strength-card fade-in-up">
                        <h3 className="comp-section-title">Signal Metrics</h3>
                        <div className="strength-grid">
                            {comparisonData.map((c, i) => {
                                const signalCount = c.features?.length || 0;
                                const conf = getAvgConf(c.features);
                                const highCount = c.features.filter(f => f.importance === 'high').length;
                                return (
                                    <div key={c.label} className="strength-item">
                                        <div className="strength-dot" style={{ background: COLORS[i] }} />
                                        <div className="strength-info">
                                            <span className="strength-name">{c.label}</span>
                                            <div className="strength-numbers">
                                                <span className="strength-big" style={{ color: COLORS[i] }}>{signalCount}</span>
                                                <span className="strength-unit">signals</span>
                                                <span className="strength-trend">
                                                    {signalCount >= 20 ? <HiOutlineTrendingUp /> : signalCount >= 8 ? <HiOutlineArrowRight /> : <HiOutlineTrendingDown />}
                                                </span>
                                            </div>
                                            <div className="strength-row">
                                                <span className="strength-conf-label">Confidence</span>
                                                <span className="strength-conf-value">{(conf * 100).toFixed(0)}%</span>
                                            </div>
                                            <div className="strength-row">
                                                <span className="strength-conf-label">High Priority</span>
                                                <span className="strength-conf-value">{highCount}</span>
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>

                    {/* ══ CHARTS SECTION ══════════════════════════════ */}
                    <div className="card comp-charts-card fade-in-up">
                        <h3 className="comp-section-title"><HiOutlineChartBar /> Visual Analytics</h3>
                        <div className="charts-grid">
                            {/* Radar Chart — Category comparison */}
                            <div className="chart-container">
                                <h4 className="chart-label">Category Radar</h4>
                                <RadarChart data={comparisonData} colors={COLOR_HEX} />
                            </div>
                            {/* Bar Chart — Signal count & confidence */}
                            <div className="chart-container">
                                <h4 className="chart-label">Signal Metrics</h4>
                                <MetricsBarChart data={comparisonData} colors={COLOR_HEX} />
                            </div>
                        </div>
                    </div>

                    {/* 6. Key Differences */}
                    {keyDifferences.length > 0 && (
                        <div className="card comp-diff-card fade-in-up">
                            <h3 className="comp-section-title">
                                <HiOutlineLightningBolt /> {mode === 'timeline' ? 'Key Changes Over Time' : 'Key Differences'}
                            </h3>
                            <ul className="diff-list">
                                {keyDifferences.map((d, i) => <li key={i} className="diff-item">{d}</li>)}
                            </ul>
                        </div>
                    )}
                </div>
            )}

            {/* Empty state */}
            {!loading && comparisonData.length === 0 && (
                <div className="empty-state">
                    <div className="icon"><HiOutlineChartBar /></div>
                    <h3>{mode === 'timeline' ? 'Select a company and reports' : 'Select companies to compare'}</h3>
                    <p>
                        {mode === 'timeline'
                            ? 'Choose a company and pick 2-3 report dates to compare intelligence over time.'
                            : 'Choose 2-3 companies from your watchlist to generate a comparative intelligence analysis.'
                        }
                    </p>
                </div>
            )}
        </div>
    );
}


/* ═══════════════════════════════════════════════════════════════════
   CHART COMPONENTS
   ═══════════════════════════════════════════════════════════════════ */

function RadarChart({ data, colors }) {
    // Build unified category labels from all companies
    const allCats = useMemo(() => {
        const catSet = new Set();
        data.forEach(c => {
            (c.features || []).forEach(f => catSet.add(f.category || 'General'));
        });
        return [...catSet].sort();
    }, [data]);

    const chartData = useMemo(() => ({
        labels: allCats,
        datasets: data.map((c, i) => {
            const dist = getCategoryDist(c.features);
            return {
                label: c.label,
                data: allCats.map(cat => dist[cat] || 0),
                backgroundColor: colors[i] + '25',  // 15% opacity fill
                borderColor: colors[i],
                borderWidth: 2,
                pointBackgroundColor: colors[i],
                pointBorderColor: '#fff',
                pointRadius: 4,
                pointHoverRadius: 6,
            };
        }),
    }), [data, allCats, colors]);

    const options = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'bottom',
                labels: {
                    padding: 16,
                    usePointStyle: true,
                    pointStyle: 'circle',
                    font: { family: "'Inter', sans-serif", size: 11, weight: 600 },
                    color: '#4A5568',
                },
            },
            tooltip: {
                backgroundColor: 'rgba(26, 29, 35, 0.92)',
                titleFont: { family: "'Inter', sans-serif", weight: 700 },
                bodyFont: { family: "'Inter', sans-serif" },
                padding: 10,
                cornerRadius: 8,
            },
        },
        scales: {
            r: {
                beginAtZero: true,
                ticks: {
                    stepSize: 1,
                    font: { size: 10 },
                    color: '#8896A6',
                    backdropColor: 'transparent',
                },
                pointLabels: {
                    font: { family: "'Inter', sans-serif", size: 10, weight: 600 },
                    color: '#4A5568',
                },
                grid: { color: 'rgba(0, 0, 0, 0.06)' },
                angleLines: { color: 'rgba(0, 0, 0, 0.06)' },
            },
        },
    };

    if (allCats.length < 3) {
        return <p style={{ color: 'var(--text-muted)', fontSize: '0.84rem', textAlign: 'center', padding: '40px 0' }}>Need at least 3 categories for radar chart</p>;
    }

    return (
        <div style={{ height: '320px' }}>
            <Radar data={chartData} options={options} />
        </div>
    );
}

function MetricsBarChart({ data, colors }) {
    const chartData = useMemo(() => ({
        labels: data.map(c => c.label),
        datasets: [
            {
                label: 'Signal Count',
                data: data.map(c => c.features?.length || 0),
                backgroundColor: colors.map(c => c + '50'),
                borderColor: colors,
                borderWidth: 2,
                borderRadius: 6,
                yAxisID: 'y',
            },
            {
                label: 'Avg Confidence (%)',
                data: data.map(c => Math.round(getAvgConf(c.features) * 100)),
                backgroundColor: colors.map(c => c + '25'),
                borderColor: colors.map(c => c + 'AA'),
                borderWidth: 2,
                borderRadius: 6,
                borderDash: [4, 4],
                yAxisID: 'y1',
            },
        ],
    }), [data, colors]);

    const options = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'bottom',
                labels: {
                    padding: 16,
                    usePointStyle: true,
                    pointStyle: 'rectRounded',
                    font: { family: "'Inter', sans-serif", size: 11, weight: 600 },
                    color: '#4A5568',
                },
            },
            tooltip: {
                backgroundColor: 'rgba(26, 29, 35, 0.92)',
                titleFont: { family: "'Inter', sans-serif", weight: 700 },
                bodyFont: { family: "'Inter', sans-serif" },
                padding: 10,
                cornerRadius: 8,
            },
        },
        scales: {
            x: {
                grid: { display: false },
                ticks: {
                    font: { family: "'Inter', sans-serif", size: 11, weight: 600 },
                    color: '#4A5568',
                },
            },
            y: {
                type: 'linear',
                position: 'left',
                beginAtZero: true,
                title: {
                    display: true,
                    text: 'Signal Count',
                    font: { family: "'Inter', sans-serif", size: 11, weight: 600 },
                    color: '#8896A6',
                },
                grid: { color: 'rgba(0, 0, 0, 0.04)' },
                ticks: { font: { size: 10 }, color: '#8896A6' },
            },
            y1: {
                type: 'linear',
                position: 'right',
                beginAtZero: true,
                max: 100,
                title: {
                    display: true,
                    text: 'Confidence %',
                    font: { family: "'Inter', sans-serif", size: 11, weight: 600 },
                    color: '#8896A6',
                },
                grid: { drawOnChartArea: false },
                ticks: { font: { size: 10 }, color: '#8896A6' },
            },
        },
    };

    return (
        <div style={{ height: '320px' }}>
            <Bar data={chartData} options={options} />
        </div>
    );
}
