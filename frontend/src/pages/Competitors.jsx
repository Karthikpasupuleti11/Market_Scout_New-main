import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    HiOutlineUserGroup,
    HiOutlinePlay,
    HiOutlineCalendar,
    HiOutlineTrash,
    HiOutlineExclamationCircle,
    HiOutlineX,
    HiOutlineTrendingUp,
    HiOutlineTrendingDown,
    HiOutlineArrowRight,
    HiOutlineDocumentText,
} from 'react-icons/hi';
import { getCompetitors, deleteCompetitor, getReports } from '../api';
import { useSettings } from '../contexts/SettingsContext';
import { WatchlistGridSkeleton } from '../components/SkeletonLoaders';
import './Competitors.css';

/* ── Format exact date/time ───────────────────────────────────── */
function formatDateTime(dateStr) {
    if (!dateStr) return '';
    return new Date(dateStr).toLocaleString([], {
        dateStyle: 'medium',
        timeStyle: 'short',
    });
}

/* ── Signal strength from feature count ────────────────────────── */
function getSignalStrength(count) {
    if (count >= 20) return { label: 'High', level: 'high' };
    if (count >= 8)  return { label: 'Medium', level: 'mid' };
    return { label: 'Low', level: 'low' };
}

export default function Competitors() {
    const [competitors, setCompetitors] = useState([]);
    const [loading, setLoading] = useState(true);
    const [confirmTarget, setConfirmTarget] = useState(null);
    const [deleting, setDeleting] = useState(false);
    const [deleteError, setDeleteError] = useState('');
    const [enriched, setEnriched] = useState({}); // { compName: { signals, summary, date } }
    const navigate = useNavigate();
    const { settings } = useSettings();

    useEffect(() => { load(); }, []);

    async function load() {
        setLoading(true);
        try {
            const data = await getCompetitors();
            setCompetitors(data);

            // Enrich each competitor with latest report data
            const enrichData = {};
            await Promise.all(data.map(async (comp) => {
                try {
                    const reports = await getReports(comp.name);
                    const reportArr = Array.isArray(reports) ? reports : [reports];
                    if (reportArr.length > 0) {
                        const latest = reportArr[0];
                        enrichData[comp.name] = {
                            signals: latest.total_features || latest.features?.length || 0,
                            sources: latest.total_sources || 0,
                            summary: latest.executive_summary || '',
                            date: latest.created_at,
                        };
                    }
                } catch { /* no reports yet */ }
            }));
            setEnriched(enrichData);
        } catch {
            setCompetitors([]);
        } finally {
            setLoading(false);
        }
    }

    function askConfirm(comp) {
        setDeleteError('');
        setConfirmTarget(comp);
    }

    function cancelConfirm() {
        if (!deleting) setConfirmTarget(null);
    }

    async function confirmDelete() {
        if (!confirmTarget) return;
        setDeleting(true);
        setDeleteError('');
        try {
            await deleteCompetitor(confirmTarget.id);
            setCompetitors(prev => prev.filter(c => c.id !== confirmTarget.id));
            setConfirmTarget(null);
        } catch (err) {
            setDeleteError(err.message || 'Failed to delete. Please try again.');
        } finally {
            setDeleting(false);
        }
    }

    return (
        <div className="competitors-page fade-in">
            <div className="page-header">
                <h1>Competitive Watchlist</h1>
                <p>Monitor and track companies across your intelligence landscape</p>
            </div>

            {loading && (
                <WatchlistGridSkeleton count={4} />
            )}

            {!loading && competitors.length === 0 && (
                <div className="empty-state">
                    <div className="icon"><HiOutlineUserGroup /></div>
                    <h3>No competitors tracked yet</h3>
                    <p>Run the intelligence pipeline on a company to start tracking them.</p>
                    <button className="btn btn-primary" style={{ marginTop: '16px' }} onClick={() => navigate('/intelligence')}>
                        <HiOutlinePlay /> Run Intelligence
                    </button>
                </div>
            )}

            {!loading && competitors.length > 0 && (
                <div className="watchlist-grid stagger">
                    {[...competitors]
                        .sort((a, b) => {
                            const dataA = enriched[a.name];
                            const dataB = enriched[b.name];
                            if (settings.watchlist.defaultSort === 'signal') {
                                return (dataB?.signals || 0) - (dataA?.signals || 0);
                            }
                            if (settings.watchlist.defaultSort === 'confidence') {
                                return (dataB?.avgConf || 0) - (dataA?.avgConf || 0);
                            }
                            // default: 'recent'
                            return new Date(b.created_at || 0) - new Date(a.created_at || 0);
                        })
                        .map((comp, i) => {
                        const data = enriched[comp.name];
                        const strength = data ? getSignalStrength(data.signals) : null;
                        const insightPreview = data?.summary
                            ? data.summary.length > 120
                                ? data.summary.slice(0, 120) + '…'
                                : data.summary
                            : null;


                        return (
                            <div key={comp.id || i} className={`card watchlist-card fade-in-up`}>
                                {/* Top row: avatar + name + strength */}
                                <div className="wl-card-top">
                                    <div className="comp-avatar">
                                        {(comp.name || '?')[0].toUpperCase()}
                                    </div>
                                    <div className="wl-card-info">
                                        <h3 className="comp-name">{comp.name}</h3>
                                        <div className="wl-card-meta">
                                            {comp.industry && (
                                                <span className="badge badge-info">{comp.industry}</span>
                                            )}
                                            {comp.created_at && (
                                                <span className="wl-time-ago">
                                                    <HiOutlineCalendar /> {formatDateTime(comp.created_at)}
                                                </span>
                                            )}
                                        </div>
                                    </div>

                                    {/* Signal strength + trend */}
                                    {strength && (
                                        <div className="wl-strength">
                                            <span className={`strength-badge ${strength.level}`}>
                                                {strength.label}
                                            </span>
                                            <span className="wl-trend">
                                                {data.signals >= 20 ? <HiOutlineTrendingUp /> :
                                                 data.signals >= 8 ? <HiOutlineArrowRight /> :
                                                 <HiOutlineTrendingDown />}
                                            </span>
                                        </div>
                                    )}
                                </div>

                                {/* Quick insight preview */}
                                {insightPreview && (
                                    <p className="wl-insight-preview">{insightPreview}</p>
                                )}

                                {/* Stats row */}
                                {data && (
                                    <div className="wl-stats-row">
                                        <span className="wl-stat"><strong>{data.signals}</strong> signals</span>
                                        <span className="wl-stat"><strong>{data.sources}</strong> sources</span>
                                    </div>
                                )}

                                {/* Actions */}
                                <div className="wl-card-actions">
                                    <button
                                        className="btn btn-secondary btn-sm"
                                        onClick={() => navigate('/intelligence', {
                                            state: { autoRunCompany: comp.name }
                                        })}
                                    >
                                        <HiOutlinePlay /> Analyze
                                    </button>
                                    <button
                                        className="btn btn-secondary btn-sm"
                                        onClick={() => navigate('/reports', {
                                            state: { autoOpenCompany: comp.name }
                                        })}
                                    >
                                        <HiOutlineDocumentText /> Reports
                                    </button>
                                    <button
                                        className="btn btn-danger btn-sm"
                                        onClick={() => askConfirm(comp)}
                                    >
                                        <HiOutlineTrash />
                                    </button>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}

            {/* ── Confirmation Modal ─────────────────────────────── */}
            {confirmTarget && (
                <div className="modal-overlay" onClick={cancelConfirm}>
                    <div
                        className="modal-box"
                        onClick={e => e.stopPropagation()}
                        role="dialog"
                        aria-modal="true"
                        aria-labelledby="confirm-title"
                    >
                        <div className="modal-header">
                            <span className="modal-icon danger">
                                <HiOutlineExclamationCircle />
                            </span>
                            <div className="modal-title-group">
                                <h2 id="confirm-title">Delete Competitor</h2>
                                <p className="modal-subtitle">This action cannot be undone.</p>
                            </div>
                            <button
                                className="modal-close"
                                onClick={cancelConfirm}
                                disabled={deleting}
                                aria-label="Close"
                            >
                                <HiOutlineX />
                            </button>
                        </div>

                        <div className="modal-body">
                            <p>
                                Are you sure you want to delete{' '}
                                <strong className="danger-text">{confirmTarget.name}</strong>?
                            </p>
                            <p className="modal-warning">
                                All associated reports and extracted features will be permanently
                                removed from the database.
                            </p>

                            {deleteError && (
                                <div className="modal-error">
                                    <HiOutlineExclamationCircle />
                                    {deleteError}
                                </div>
                            )}
                        </div>

                        <div className="modal-footer">
                            <button className="btn btn-secondary" onClick={cancelConfirm} disabled={deleting}>
                                Cancel
                            </button>
                            <button
                                className="btn btn-danger"
                                onClick={confirmDelete}
                                disabled={deleting}
                                id="confirm-delete-btn"
                            >
                                {deleting ? (
                                    <><span className="spinner spinner-sm" /> Deleting…</>
                                ) : (
                                    <><HiOutlineTrash /> Yes, Delete</>
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
