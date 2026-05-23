/**
 * EmptyState — Premium empty state component
 *
 * Replaces plain icon + text with an animated, illustrated
 * empty state that guides users to their next action.
 */

import { HiOutlineArrowRight } from 'react-icons/hi';
import './EmptyState.css';

/* ── Inline SVG Illustrations ──────────────────────────────────── */

function ReportsIllustration() {
  return (
    <svg className="es-illustration" viewBox="0 0 200 160" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Stacked documents */}
      <rect x="50" y="40" width="100" height="110" rx="8" fill="var(--bg-input)" stroke="var(--border-default)" strokeWidth="1.5"/>
      <rect x="42" y="48" width="100" height="110" rx="8" fill="var(--bg-card)" stroke="var(--border-default)" strokeWidth="1.5"/>
      {/* Lines on doc */}
      <rect x="58" y="68" width="60" height="4" rx="2" fill="var(--border-accent)" opacity="0.6"/>
      <rect x="58" y="80" width="72" height="4" rx="2" fill="var(--bg-input)"/>
      <rect x="58" y="90" width="50" height="4" rx="2" fill="var(--bg-input)"/>
      <rect x="58" y="100" width="65" height="4" rx="2" fill="var(--bg-input)"/>
      <rect x="58" y="114" width="40" height="4" rx="2" fill="var(--bg-input)"/>
      {/* Magnifying glass */}
      <circle cx="135" cy="42" r="18" stroke="var(--accent-primary)" strokeWidth="2.5" fill="none" opacity="0.7">
        <animate attributeName="r" values="18;20;18" dur="3s" repeatCount="indefinite"/>
      </circle>
      <line x1="148" y1="55" x2="160" y2="67" stroke="var(--accent-primary)" strokeWidth="2.5" strokeLinecap="round" opacity="0.7"/>
      {/* Sparkle */}
      <circle cx="130" cy="35" r="2" fill="var(--accent-primary)" opacity="0.5">
        <animate attributeName="opacity" values="0.5;1;0.5" dur="2s" repeatCount="indefinite"/>
      </circle>
    </svg>
  );
}

function CompetitorsIllustration() {
  return (
    <svg className="es-illustration" viewBox="0 0 200 160" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* People silhouettes */}
      <circle cx="70" cy="60" r="16" fill="var(--bg-input)" stroke="var(--border-default)" strokeWidth="1.5"/>
      <rect x="54" y="82" width="32" height="40" rx="10" fill="var(--bg-input)" stroke="var(--border-default)" strokeWidth="1.5"/>
      <circle cx="100" cy="50" r="18" fill="var(--accent-soft)" stroke="var(--border-accent)" strokeWidth="1.5">
        <animate attributeName="r" values="18;19;18" dur="3s" repeatCount="indefinite"/>
      </circle>
      <rect x="82" y="74" width="36" height="44" rx="12" fill="var(--accent-soft)" stroke="var(--border-accent)" strokeWidth="1.5"/>
      <circle cx="130" cy="60" r="16" fill="var(--bg-input)" stroke="var(--border-default)" strokeWidth="1.5"/>
      <rect x="114" y="82" width="32" height="40" rx="10" fill="var(--bg-input)" stroke="var(--border-default)" strokeWidth="1.5"/>
      {/* Connection lines */}
      <line x1="82" y1="60" x2="86" y2="56" stroke="var(--accent-primary)" strokeWidth="1" strokeDasharray="3 3" opacity="0.4"/>
      <line x1="118" y1="60" x2="114" y2="56" stroke="var(--accent-primary)" strokeWidth="1" strokeDasharray="3 3" opacity="0.4"/>
      {/* Radar pulse */}
      <circle cx="100" cy="50" r="30" stroke="var(--accent-primary)" strokeWidth="1" fill="none" opacity="0.15">
        <animate attributeName="r" values="30;45;30" dur="3s" repeatCount="indefinite"/>
        <animate attributeName="opacity" values="0.15;0;0.15" dur="3s" repeatCount="indefinite"/>
      </circle>
    </svg>
  );
}

function AnalysisIllustration() {
  return (
    <svg className="es-illustration" viewBox="0 0 200 160" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Chart bars */}
      <rect x="40" y="100" width="24" height="50" rx="4" fill="var(--bg-input)" stroke="var(--border-default)" strokeWidth="1.5"/>
      <rect x="72" y="70" width="24" height="80" rx="4" fill="var(--accent-soft)" stroke="var(--border-accent)" strokeWidth="1.5">
        <animate attributeName="height" values="80;85;80" dur="2.5s" repeatCount="indefinite"/>
        <animate attributeName="y" values="70;65;70" dur="2.5s" repeatCount="indefinite"/>
      </rect>
      <rect x="104" y="85" width="24" height="65" rx="4" fill="var(--bg-input)" stroke="var(--border-default)" strokeWidth="1.5"/>
      <rect x="136" y="55" width="24" height="95" rx="4" fill="var(--info-bg)" stroke="var(--border-default)" strokeWidth="1.5">
        <animate attributeName="height" values="95;100;95" dur="3s" repeatCount="indefinite"/>
        <animate attributeName="y" values="55;50;55" dur="3s" repeatCount="indefinite"/>
      </rect>
      {/* Trend line */}
      <polyline points="52,95 84,65 116,80 148,48" stroke="var(--accent-primary)" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" opacity="0.6"/>
      {/* Data points */}
      <circle cx="52" cy="95" r="3" fill="var(--accent-primary)" opacity="0.8"/>
      <circle cx="84" cy="65" r="3" fill="var(--accent-primary)" opacity="0.8"/>
      <circle cx="116" cy="80" r="3" fill="var(--accent-primary)" opacity="0.8"/>
      <circle cx="148" cy="48" r="4" fill="var(--accent-primary)" opacity="0.8">
        <animate attributeName="r" values="4;5;4" dur="2s" repeatCount="indefinite"/>
      </circle>
    </svg>
  );
}

function ScheduleIllustration() {
  return (
    <svg className="es-illustration" viewBox="0 0 200 160" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Calendar */}
      <rect x="45" y="40" width="110" height="100" rx="10" fill="var(--bg-card)" stroke="var(--border-default)" strokeWidth="1.5"/>
      <rect x="45" y="40" width="110" height="28" rx="10" fill="var(--accent-soft)"/>
      <rect x="45" y="58" width="110" height="10" fill="var(--accent-soft)"/>
      {/* Calendar dots */}
      <circle cx="68" cy="54" r="3" fill="var(--accent-primary)" opacity="0.6"/>
      <circle cx="88" cy="54" r="3" fill="var(--accent-primary)" opacity="0.6"/>
      <circle cx="108" cy="54" r="3" fill="var(--accent-primary)" opacity="0.6"/>
      {/* Calendar grid lines */}
      <rect x="58" y="80" width="14" height="10" rx="3" fill="var(--bg-input)"/>
      <rect x="78" y="80" width="14" height="10" rx="3" fill="var(--bg-input)"/>
      <rect x="98" y="80" width="14" height="10" rx="3" fill="var(--bg-input)"/>
      <rect x="118" y="80" width="14" height="10" rx="3" fill="var(--bg-input)"/>
      <rect x="58" y="98" width="14" height="10" rx="3" fill="var(--bg-input)"/>
      <rect x="78" y="98" width="14" height="10" rx="3" fill="var(--accent-soft)" stroke="var(--border-accent)" strokeWidth="1">
        <animate attributeName="opacity" values="1;0.5;1" dur="2s" repeatCount="indefinite"/>
      </rect>
      <rect x="98" y="98" width="14" height="10" rx="3" fill="var(--bg-input)"/>
      <rect x="118" y="98" width="14" height="10" rx="3" fill="var(--bg-input)"/>
      <rect x="58" y="116" width="14" height="10" rx="3" fill="var(--bg-input)"/>
      <rect x="78" y="116" width="14" height="10" rx="3" fill="var(--bg-input)"/>
      {/* Clock */}
      <circle cx="155" cy="125" r="16" fill="var(--bg-card)" stroke="var(--accent-primary)" strokeWidth="1.5" opacity="0.7"/>
      <line x1="155" y1="125" x2="155" y2="115" stroke="var(--accent-primary)" strokeWidth="1.5" strokeLinecap="round" opacity="0.7">
        <animateTransform attributeName="transform" type="rotate" values="0 155 125;360 155 125" dur="8s" repeatCount="indefinite"/>
      </line>
      <line x1="155" y1="125" x2="163" y2="125" stroke="var(--accent-primary)" strokeWidth="1.5" strokeLinecap="round" opacity="0.5"/>
    </svg>
  );
}

const ILLUSTRATIONS = {
  reports: ReportsIllustration,
  competitors: CompetitorsIllustration,
  analysis: AnalysisIllustration,
  schedule: ScheduleIllustration,
};

/* ── Main Component ────────────────────────────────────────────── */

export default function EmptyState({
  illustration = 'reports',
  icon,
  title,
  description,
  buttonText,
  buttonIcon,
  onClick,
  hint,
}) {
  const Illustration = ILLUSTRATIONS[illustration];

  return (
    <div className="enhanced-empty-state fade-in-up">
      <div className="es-glow" />

      {/* Floating decorative dots */}
      <div className="es-dots">
        <span className="es-dot es-dot-1" />
        <span className="es-dot es-dot-2" />
        <span className="es-dot es-dot-3" />
      </div>

      {Illustration ? (
        <Illustration />
      ) : icon ? (
        <div className="es-icon-fallback">{icon}</div>
      ) : null}

      <h3 className="es-title">{title}</h3>
      <p className="es-description">{description}</p>

      {buttonText && (
        <button className="btn btn-primary es-cta" onClick={onClick}>
          {buttonIcon || null}
          {buttonText}
          <HiOutlineArrowRight className="es-cta-arrow" />
        </button>
      )}

      {hint && <p className="es-hint">{hint}</p>}
    </div>
  );
}
