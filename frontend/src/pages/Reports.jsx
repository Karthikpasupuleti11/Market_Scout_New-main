import { useState, useEffect, useRef } from "react";
import { useNavigate, useLocation } from "react-router-dom";

import {
  HiOutlineSearch,
  HiOutlineDocumentText,
  HiOutlineExternalLink,
  HiChevronDown,
  HiChevronUp,
  HiOutlineDownload,
  HiOutlineTrash,
  HiOutlineExclamationCircle,
  HiOutlineX,
  HiOutlineSparkles,
} from "react-icons/hi";
import { getReports, deleteReport } from "../api";
import { generateReportPDF } from "../utils/pdfExport";
import ReportAssistant from '../components/ReportAssistant';
import './Reports.css';

export default function Reports() {
  const navigate = useNavigate();
  const location = useLocation();
  const autoSearched = useRef(false);

  const [company, setCompany] = useState("");
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [expanded, setExpanded] = useState(null);
  const [pdfLoadingIdx, setPdfLoadingIdx] = useState(null);
  const assistantRefs = useRef({});

  // Delete modal state
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState('');

  const handleCompanyChange = (value) => {
    setCompany(value);
    if (!value.trim()) {
      setReports([]);
      setSearched(false);
      setExpanded(null);
    }
  };

  const handleDownloadPDF = async (report, idx) => {
    setPdfLoadingIdx(idx);
    try {
      await new Promise(r => setTimeout(r, 50));
      generateReportPDF(report, company);
    } finally {
      setPdfLoadingIdx(null);
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!company.trim()) return;
    setLoading(true);
    setSearched(true);
    try {
      const data = await getReports(company.trim());
      const reportsArr = Array.isArray(data) ? data : [data];
      // Inject company_name so ReportAssistant RAG can build a session ID
      setReports(reportsArr.map(r => ({ ...r, company_name: company.trim() })));
    } catch {
      setReports([]);
    } finally {
      setLoading(false);
    }
  };

  // Auto-search if navigated from Watchlist with autoOpenCompany
  useEffect(() => {
    const auto = location.state?.autoOpenCompany;
    if (auto && !autoSearched.current) {
      autoSearched.current = true;
      setCompany(auto);
      // Trigger search after state update
      (async () => {
        setLoading(true);
        setSearched(true);
        try {
          const data = await getReports(auto.trim());
          const reportsArr = Array.isArray(data) ? data : [data];
          setReports(reportsArr.map(r => ({ ...r, company_name: auto.trim() })));
        } catch {
          setReports([]);
        } finally {
          setLoading(false);
        }
      })();
    }
  }, [location.state]);

  function askDelete(report, idx) {
    setDeleteError('');
    setDeleteTarget({ report, idx });
  }

  function cancelDelete() {
    if (!deleting) setDeleteTarget(null);
  }

  async function confirmDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    setDeleteError('');
    try {
      await deleteReport(deleteTarget.report.id);
      setReports(prev => prev.filter((_, i) => i !== deleteTarget.idx));
      setDeleteTarget(null);
    } catch (err) {
      setDeleteError(err.message || 'Failed to delete. Please try again.');
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="reports-page fade-in">
      <div className="page-header">
        <h1>Intelligence Archives</h1>
        <p>Search and browse historical analysis reports — access executive summaries, signals, and evidence</p>
      </div>

      <div className="card reports-hero-strip fade-in-up">
        <div className="reports-hero-item">
          <span>Search Query</span>
          <strong>{company?.trim() ? company : "No company selected"}</strong>
        </div>
        <div className="reports-hero-item">
          <span>Results</span>
          <strong>{loading ? "Searching..." : `${reports.length} reports`}</strong>
        </div>
        <div className="reports-hero-item">
          <span>State</span>
          <strong>{loading ? "In progress" : searched ? "Completed" : "Ready"}</strong>
        </div>
      </div>

      {/* Search Form */}
      <form className="card report-search-card" onSubmit={handleSearch}>
        <div className="report-search-row">
          <div className="report-search-wrapper">
            <HiOutlineSearch className="report-search-icon" />
            <input
              className="input report-search-input"
              placeholder="Search reports by company name..."
              value={company}
              onChange={(e) => handleCompanyChange(e.target.value)}
            />
          </div>
          <button
            type="submit"
            className="btn btn-primary report-search-btn"
            disabled={loading || !company.trim()}
          >
            {loading ? <span className="spinner" /> : <><HiOutlineSearch /> Search</>}
          </button>
        </div>
      </form>

      {loading && (
        <div className="card reports-loading-card">
          <div className="spinner spinner-lg reports-loading-spinner" />
          <p>Searching reports...</p>
        </div>
      )}

      {searched && !loading && reports.length === 0 && (
        <div className="empty-state">
          <div className="icon"><HiOutlineDocumentText /></div>
          <h3>Report not found</h3>
          <p>No intelligence report exists for "{company}". Do you want to generate one now?</p>
          <button
            className="btn btn-primary"
            style={{ marginTop: '16px' }}
            onClick={() => navigate('/intelligence', {
              state: { autoRunCompany: company.trim() }
            })}
          >
            <HiOutlineSearch /> Generate Report
          </button>
        </div>
      )}

      {!loading && reports.length > 0 && (
        <div className="reports-list stagger">
          {reports.map((report, i) => {
            const isOpen = expanded === i;
            const avgConf = getAvgConfidence(report);
            const insightPreview = report.executive_summary
              ? report.executive_summary.length > 140
                ? report.executive_summary.slice(0, 140) + '…'
                : report.executive_summary
              : null;

            return (
              <div key={report.id || i} className={`card report-card fade-in-up ${isOpen ? 'open' : ''}`}>
                <div className="report-card-header" onClick={() => setExpanded(isOpen ? null : i)}>
                  <div className="report-icon"><HiOutlineDocumentText /></div>
                  <div className="report-info">
                    <h3>{report.company_name || company}</h3>
                    <div className="report-meta-row">
                      {report.created_at && (
                        <span>{new Date(report.created_at).toLocaleDateString([], { dateStyle: 'medium' })}</span>
                      )}
                      <span className="meta-dot">·</span>
                      <span>{report.total_features || 0} signals</span>
                      <span className="meta-dot">·</span>
                      <span>{report.total_sources || 0} sources</span>
                      {avgConf > 0 && (
                        <>
                          <span className="meta-dot">·</span>
                          <span className={`report-conf ${avgConf >= 70 ? 'high' : avgConf >= 40 ? 'mid' : 'low'}`}>
                            {avgConf}% confidence
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                  <div className="report-actions">
                    <button
                      className="btn btn-pdf btn-pdf-sm"
                      onClick={e => { e.stopPropagation(); handleDownloadPDF(report, i); }}
                      disabled={pdfLoadingIdx === i}
                      title="Download as PDF"
                    >
                      {pdfLoadingIdx === i ? (
                        <><span className="spinner spinner-sm" /> PDF</>
                      ) : (
                        <><HiOutlineDownload /> PDF</>
                      )}
                    </button>
                    <button
                      className="btn btn-primary btn-sm"
                      onClick={e => { 
                        e.stopPropagation(); 
                        setExpanded(expanded === i ? expanded : i);
                        setTimeout(() => {
                          assistantRefs.current[i]?.triggerIndex();
                        }, 100);
                      }}
                      title="Ask Report Assistant"
                    >
                      <HiOutlineSparkles /> Ask AI
                    </button>
                    <button
                      className="btn btn-danger btn-sm"
                      onClick={e => { e.stopPropagation(); askDelete(report, i); }}
                      title="Delete report"
                    >
                      <HiOutlineTrash />
                    </button>
                    <span className="report-expand-icon">
                      {isOpen ? <HiChevronUp /> : <HiChevronDown />}
                    </span>
                  </div>
                </div>

                {!isOpen && insightPreview && (
                  <p className="report-insight-preview">{insightPreview}</p>
                )}

                {isOpen && (
                  <div className="report-details fade-in">
                    {report.executive_summary && (
                      <div className="report-summary-section">
                        <h4>Executive Insight</h4>
                        <p>{report.executive_summary}</p>
                      </div>
                    )}
                    {report.all_sources && report.all_sources.length > 0 && (
                      <div className="report-sources-section">
                        <h4>Sources ({report.all_sources.length})</h4>
                        <div className="report-sources-list">
                          {report.all_sources.map((url, j) => (
                            <a key={j} href={url} target="_blank" rel="noopener noreferrer" className="evidence-item">
                              <HiOutlineExternalLink className="evidence-link-icon" />
                              <span>{url.length > 80 ? url.slice(0, 80) + '...' : url}</span>
                            </a>
                          ))}
                        </div>
                      </div>
                    )}
                    {/* Report Assistant RAG UI */}
                    <div>
                      <ReportAssistant report={report} ref={el => assistantRefs.current[i] = el} />
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* ── Delete Confirmation Modal ──────────────────────── */}
      {deleteTarget && (
        <div className="modal-overlay" onClick={cancelDelete}>
          <div className="modal-box" onClick={e => e.stopPropagation()} role="dialog" aria-modal="true">
            <div className="modal-header">
              <span className="modal-icon danger"><HiOutlineExclamationCircle /></span>
              <div className="modal-title-group">
                <h2>Delete Report</h2>
                <p className="modal-subtitle">This action cannot be undone.</p>
              </div>
              <button className="modal-close" onClick={cancelDelete} disabled={deleting} aria-label="Close">
                <HiOutlineX />
              </button>
            </div>
            <div className="modal-body">
              <p>
                Are you sure you want to delete the report for{' '}
                <strong className="danger-text">{deleteTarget.report.company_name || company}</strong>
                {deleteTarget.report.created_at && (
                  <> from <strong>{new Date(deleteTarget.report.created_at).toLocaleDateString([], { dateStyle: 'medium' })}</strong></>
                )}?
              </p>
              <p className="modal-warning">
                All {deleteTarget.report.total_features || 0} signals and associated data from this report will be permanently removed.
              </p>
              {deleteError && (
                <div className="modal-error"><HiOutlineExclamationCircle /> {deleteError}</div>
              )}
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={cancelDelete} disabled={deleting}>Cancel</button>
              <button className="btn btn-danger" onClick={confirmDelete} disabled={deleting}>
                {deleting ? <><span className="spinner spinner-sm" /> Deleting…</> : <><HiOutlineTrash /> Yes, Delete</>}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function getAvgConfidence(report) {
  const features = report.features || [];
  if (features.length === 0) return 0;
  const scores = features.map(f => f.confidence_score ?? f.confidence).filter(s => s != null);
  if (scores.length === 0) return 0;
  return Math.round((scores.reduce((a, b) => a + b, 0) / scores.length) * 100);
}