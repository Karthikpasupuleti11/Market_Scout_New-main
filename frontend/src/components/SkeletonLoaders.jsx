/**
 * SkeletonLoaders — Reusable shimmer loading placeholders
 *
 * Matches the Market Scout design system (--bg-input, --border-subtle, etc.)
 * Uses the existing `shimmer` keyframe from index.css.
 */

import './SkeletonLoaders.css';

/* ── Primitive ─────────────────────────────────────────────────── */

export function SkeletonLine({ width = '100%', height = '14px', style }) {
  return <div className="sk-line" style={{ width, height, ...style }} />;
}

export function SkeletonCircle({ size = '48px', style }) {
  return <div className="sk-circle" style={{ width: size, height: size, ...style }} />;
}

/* ── Dashboard: Hero KPI Strip ─────────────────────────────────── */

export function DashboardHeroSkeleton() {
  return (
    <div className="sk-dashboard-hero card fade-in">
      <div className="sk-hero-content">
        <SkeletonLine width="140px" height="12px" />
        <SkeletonLine width="320px" height="28px" style={{ marginTop: 12 }} />
        <SkeletonLine width="480px" height="16px" style={{ marginTop: 10 }} />
        <SkeletonLine width="180px" height="13px" style={{ marginTop: 16 }} />
      </div>
      <div className="sk-hero-kpis">
        {[1, 2, 3].map(i => (
          <div key={i} className="sk-hero-kpi">
            <SkeletonLine width="80px" height="11px" />
            <SkeletonLine width="120px" height="18px" style={{ marginTop: 6 }} />
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Dashboard: Stat Cards ─────────────────────────────────────── */

export function StatCardSkeleton() {
  return (
    <div className="stat-card sk-stat-card fade-in-up">
      <div className="sk-stat-icon sk-shimmer" />
      <div className="stat-info">
        <SkeletonLine width="48px" height="22px" />
        <SkeletonLine width="100px" height="12px" style={{ marginTop: 6 }} />
      </div>
    </div>
  );
}

export function StatsGridSkeleton({ count = 4 }) {
  return (
    <div className="stats-grid stagger">
      {Array.from({ length: count }).map((_, i) => (
        <StatCardSkeleton key={i} />
      ))}
    </div>
  );
}

/* ── Watchlist / Competitor Cards ───────────────────────────────── */

export function WatchlistCardSkeleton() {
  return (
    <div className="card sk-watchlist-card fade-in-up">
      <div className="sk-wl-top">
        <SkeletonCircle size="44px" />
        <div className="sk-wl-info">
          <SkeletonLine width="140px" height="18px" />
          <div className="sk-wl-meta">
            <SkeletonLine width="60px" height="20px" style={{ borderRadius: '12px' }} />
            <SkeletonLine width="130px" height="12px" />
          </div>
        </div>
        <SkeletonLine width="56px" height="22px" style={{ borderRadius: '12px', marginLeft: 'auto' }} />
      </div>
      <SkeletonLine width="100%" height="13px" style={{ marginTop: 16 }} />
      <SkeletonLine width="85%" height="13px" style={{ marginTop: 6 }} />
      <div className="sk-wl-stats">
        <SkeletonLine width="80px" height="14px" />
        <SkeletonLine width="80px" height="14px" />
      </div>
      <div className="sk-wl-actions">
        <SkeletonLine width="90px" height="32px" style={{ borderRadius: '8px' }} />
        <SkeletonLine width="90px" height="32px" style={{ borderRadius: '8px' }} />
        <SkeletonLine width="40px" height="32px" style={{ borderRadius: '8px' }} />
      </div>
    </div>
  );
}

export function WatchlistGridSkeleton({ count = 4 }) {
  return (
    <div className="watchlist-grid stagger">
      {Array.from({ length: count }).map((_, i) => (
        <WatchlistCardSkeleton key={i} />
      ))}
    </div>
  );
}

/* ── Report Card ───────────────────────────────────────────────── */

export function ReportCardSkeleton() {
  return (
    <div className="card sk-report-card fade-in-up">
      <div className="sk-report-header">
        <div className="sk-report-icon sk-shimmer" />
        <div className="sk-report-info">
          <SkeletonLine width="160px" height="18px" />
          <div className="sk-report-meta">
            <SkeletonLine width="90px" height="12px" />
            <SkeletonLine width="70px" height="12px" />
            <SkeletonLine width="70px" height="12px" />
          </div>
        </div>
        <div className="sk-report-actions">
          <SkeletonLine width="64px" height="30px" style={{ borderRadius: '8px' }} />
          <SkeletonLine width="72px" height="30px" style={{ borderRadius: '8px' }} />
          <SkeletonLine width="36px" height="30px" style={{ borderRadius: '8px' }} />
        </div>
      </div>
      <SkeletonLine width="100%" height="13px" style={{ marginTop: 16 }} />
      <SkeletonLine width="70%" height="13px" style={{ marginTop: 6 }} />
    </div>
  );
}

export function ReportsListSkeleton({ count = 3 }) {
  return (
    <div className="reports-list stagger">
      {Array.from({ length: count }).map((_, i) => (
        <ReportCardSkeleton key={i} />
      ))}
    </div>
  );
}

/* ── Analysis / Comparison Loading ─────────────────────────────── */

export function AnalysisResultsSkeleton() {
  return (
    <div className="sk-analysis-results fade-in">
      {/* Executive summary card */}
      <div className="card card-accent sk-analysis-exec">
        <SkeletonLine width="180px" height="13px" />
        <SkeletonLine width="100%" height="16px" style={{ marginTop: 14 }} />
        <SkeletonLine width="90%" height="16px" style={{ marginTop: 8 }} />
        <div className="sk-analysis-exec-blocks">
          {[1, 2].map(i => (
            <div key={i} className="sk-exec-block">
              <div className="sk-exec-block-header">
                <SkeletonCircle size="10px" />
                <SkeletonLine width="100px" height="14px" />
              </div>
              <SkeletonLine width="100%" height="12px" style={{ marginTop: 10 }} />
              <SkeletonLine width="80%" height="12px" style={{ marginTop: 6 }} />
              <SkeletonLine width="60%" height="12px" style={{ marginTop: 6 }} />
            </div>
          ))}
        </div>
      </div>

      {/* Charts card */}
      <div className="card sk-charts-card">
        <SkeletonLine width="160px" height="16px" />
        <div className="sk-charts-grid">
          <div className="sk-chart-placeholder sk-shimmer" />
          <div className="sk-chart-placeholder sk-shimmer" />
        </div>
      </div>

      {/* Signals card */}
      <div className="card sk-signals-card">
        <SkeletonLine width="200px" height="16px" />
        <div className="sk-signals-cols">
          {[1, 2].map(i => (
            <div key={i} className="sk-signals-col">
              <div className="sk-signals-col-header">
                <SkeletonCircle size="10px" />
                <SkeletonLine width="80px" height="14px" />
              </div>
              {[1, 2, 3].map(j => (
                <div key={j} className="sk-signal-item">
                  <SkeletonLine width="90%" height="14px" />
                  <SkeletonLine width="100%" height="11px" style={{ marginTop: 6 }} />
                  <SkeletonLine width="60%" height="11px" style={{ marginTop: 4 }} />
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ── Schedule: Job List ────────────────────────────────────────── */

export function ScheduleJobSkeleton({ count = 3 }) {
  return (
    <div className="sk-jobs-list">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="sk-job-row fade-in-up" style={{ animationDelay: `${i * 0.06}s` }}>
          <div className="sk-job-info">
            <div className="sk-job-title-row">
              <SkeletonLine width="120px" height="16px" />
              <SkeletonLine width="60px" height="20px" style={{ borderRadius: '12px' }} />
            </div>
            <div className="sk-job-meta">
              <SkeletonLine width="140px" height="12px" />
              <SkeletonLine width="160px" height="12px" />
            </div>
          </div>
          <SkeletonLine width="36px" height="30px" style={{ borderRadius: '8px' }} />
        </div>
      ))}
    </div>
  );
}
