import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { getCompetitors, getHealth, getDashboardStats } from "../api";
import { useSettings } from "../contexts/SettingsContext";
import {
  HiOutlineLightningBolt,
  HiOutlineDocumentText,
  HiOutlineEye,
  HiOutlineShieldCheck,
  HiOutlineGlobeAlt,
  HiOutlineChevronRight,
} from "react-icons/hi";
import ThemeToggle from "./ThemeToggle";
import './Dashboard.css';

export default function Dashboard() {
  const [competitors, setCompetitors] = useState([]);
  const [health, setHealth] = useState(null);
  const [dashStats, setDashStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const { settings } = useSettings();

  useEffect(() => {
    async function load() {
      try {
        const [compData, healthData, statsData] = await Promise.all([
          getCompetitors().catch(() => []),
          getHealth().catch(() => null),
          getDashboardStats().catch(() => null),
        ]);
        setCompetitors(compData);
        setHealth(healthData);
        setDashStats(statsData);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  // Derive dashboard KPIs from the latest report (not watchlist)
  const latestReport = dashStats?.latest_report;

  const latestRunDate = latestReport?.created_at
    ? new Date(latestReport.created_at).toLocaleDateString([], { dateStyle: 'medium' })
    : 'No runs yet';

  const recentFocus = latestReport?.company_name || 'No company yet';

  const freshnessLabel = latestReport?.created_at
    ? (() => {
        const daysAgo = Math.max(0, Math.floor(
          (Date.now() - new Date(latestReport.created_at).getTime()) / (1000 * 60 * 60 * 24)
        ));
        if (daysAgo === 0) return 'Today';
        if (daysAgo === 1) return '1 day ago';
        return `${daysAgo} days ago`;
      })()
    : 'Awaiting first run';

  const recencyWindow = `${settings?.analysis?.timeWindow || 7} Days`;

  return (
    <div className="overview-page fade-in">

      {/* ── Hero Header ─────────────────────────────────────── */}
      <div className="overview-hero">
        <div className="card overview-hero-surface fade-in-up">
          <div className="hero-content">
            <div className="hero-badge">
              <span className="hero-badge-dot" />
              {health ? "All Systems Operational" : "Connecting..."}
            </div>
            <h1>Market Intelligence Overview</h1>
            <p>AI-powered competitive intelligence — discover, verify, and track technical signals from public sources in real-time.</p>
            {latestReport && (
              <div className="hero-last-run">
                Last analysis: {latestRunDate} — {recentFocus}
              </div>
            )}
          </div>
          <div className="hero-kpis">
            <div className="hero-kpi">
              <span>Last analyzed</span>
              <strong>{loading ? 'Loading...' : latestRunDate}</strong>
            </div>
            <div className="hero-kpi">
              <span>Recent focus</span>
              <strong>{loading ? 'Loading...' : recentFocus}</strong>
            </div>
            <div className="hero-kpi">
              <span>Data freshness</span>
              <strong>{loading ? 'Loading...' : freshnessLabel}</strong>
            </div>
          </div>
        </div>
      </div>

      {/* ── Stats ────────────────────────────────────────────── */}
      <div className="stats-grid stagger">
        <StatCard
          icon={<HiOutlineEye />}
          value={loading ? "—" : (dashStats?.total_companies ?? competitors.length)}
          label="Tracked Companies"
          color="var(--info)"
          bg="var(--info-bg)"
        />
        <StatCard
          icon={<HiOutlineShieldCheck />}
          value={health ? "Online" : "—"}
          label="System Status"
          color="var(--success)"
          bg="var(--success-bg)"
        />
        <StatCard
          icon={<HiOutlineGlobeAlt />}
          value="11"
          label="Pipeline Stages"
          color="var(--purple)"
          bg="var(--purple-bg)"
        />
        <StatCard
          icon={<HiOutlineLightningBolt />}
          value={recencyWindow}
          label="Recency Window"
          color="var(--warning)"
          bg="var(--warning-bg)"
        />
      </div>

      {/* ── Quick Actions ────────────────────────────────────── */}
      <div className="actions-grid stagger">
        <ActionCard
          icon={<HiOutlineLightningBolt />}
          title="Run Intelligence"
          desc="Analyze a company's technical landscape and discover competitive signals."
          color="var(--accent-primary)"
          bg="var(--accent-soft)"
          onClick={() => navigate("/intelligence")}
        />
        <ActionCard
          icon={<HiOutlineDocumentText />}
          title="Browse Reports"
          desc="Access historical intelligence reports with executive summaries and evidence."
          color="var(--info)"
          bg="var(--info-bg)"
          onClick={() => navigate("/reports")}
        />
        <ActionCard
          icon={<HiOutlineEye />}
          title="Competitive Watchlist"
          desc="View and manage the companies in your intelligence monitoring pipeline."
          color="var(--warning)"
          bg="var(--warning-bg)"
          onClick={() => navigate("/watchlist")}
        />
      </div>

      {/* ── Pipeline Architecture ────────────────────────────── */}
      <div className="card pipeline-section fade-in-up">
        <div className="pipeline-header">
          <h3>Pipeline Architecture</h3>
          <span className="pipeline-meta">11-stage intelligence pipeline</span>
        </div>

        <div className="pipeline-phases">
          {PIPELINE_PHASES.map((phase, pi) => (
            <div key={pi} className="pipeline-phase">
              <div className="phase-label">{phase.label}</div>
              <div className="phase-steps stagger">
                {phase.steps.map((step, si) => (
                  <div key={si} className="pipeline-node">
                    <div className="node-number">{step.num}</div>
                    <div className="node-info">
                      <span className="node-label">{step.label}</span>
                      <span className="node-desc">{step.desc}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ── Sub-Components ────────────────────────────────────────────── */

function StatCard({ icon, value, label, color, bg }) {
  return (
    <div className="stat-card fade-in-up">
      <div className="stat-icon" style={{ background: bg, color }}>
        {icon}
      </div>
      <div className="stat-info">
        <h3>{typeof value === 'number' ? <AnimatedValue target={value} /> : value}</h3>
        <p>{label}</p>
      </div>
    </div>
  );
}

/* Animated counter hook */
function AnimatedValue({ target, duration = 800 }) {
  const [current, setCurrent] = useState(0);
  const startTime = useRef(null);
  const rafId = useRef(null);

  useEffect(() => {
    if (target === 0) { setCurrent(0); return; }
    startTime.current = performance.now();

    function tick(now) {
      const elapsed = now - startTime.current;
      const progress = Math.min(elapsed / duration, 1);
      // ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setCurrent(Math.round(eased * target));
      if (progress < 1) {
        rafId.current = requestAnimationFrame(tick);
      }
    }

    rafId.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafId.current);
  }, [target, duration]);

  return <>{current}</>;
}

function ActionCard({ icon, title, desc, color, bg, onClick }) {
  return (
    <div className="action-card card fade-in-up" onClick={onClick}>
      <div className="action-icon" style={{ background: bg, color }}>
        {icon}
      </div>
      <div className="action-content">
        <h3>{title}</h3>
        <p>{desc}</p>
      </div>
      <HiOutlineChevronRight className="action-arrow" />
    </div>
  );
}

/* ── Pipeline Data — Grouped by Phase ──────────────────────────── */

const PIPELINE_PHASES = [
  {
    label: "Ingest",
    steps: [
      { num: "1", label: "Guardrails", desc: "Security checks" },
      { num: "2", label: "Search Planning", desc: "Query generation" },
      { num: "3", label: "Web Search", desc: "Multi-source" },
    ],
  },
  {
    label: "Process",
    steps: [
      { num: "4", label: "Smart Scraping", desc: "3-tier cascade" },
      { num: "5", label: "Date Validation", desc: "Recency filter" },
      { num: "6", label: "Content Filter", desc: "Relevance check" },
      { num: "7", label: "Authority Check", desc: "Credibility score" },
    ],
  },
  {
    label: "Analyze",
    steps: [
      { num: "8", label: "Extraction", desc: "Signal discovery" },
      { num: "9", label: "Verification", desc: "Cross-source" },
      { num: "10", label: "Scoring", desc: "Confidence rating" },
      { num: "11", label: "Synthesis", desc: "Report generation" },
    ],
  },
];
