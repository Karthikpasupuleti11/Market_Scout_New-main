import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { HiOutlineArrowRight, HiOutlineArrowLeft, HiOutlineCheck, HiOutlineX } from 'react-icons/hi';
import { TOUR_STEPS } from './tourSteps';
import './GuidedTour.css';

/* ═══════════════════════════════════════════════════════════════════
   GUIDED TOUR — Cross-page walkthrough
   - Dynamic arrow that actually points at the target element
   - No aggressive scrolling
   - Tooltip clamped above system taskbar
   ═══════════════════════════════════════════════════════════════════ */

const LS_KEY = 'market_scout_tour_seen';

export default function GuidedTour({ isOpen, onClose }) {
  const [step, setStep] = useState(0);
  const [targetRect, setTargetRect] = useState(null);
  const navigate = useNavigate();
  const location = useLocation();
  const timerRef = useRef(null);

  const current = TOUR_STEPS[step];
  const total = TOUR_STEPS.length;
  const isFirst = step === 0;
  const isLast = step === total - 1;

  /* ── Find and measure target ─────────────────────────────────── */
  const measureTarget = useCallback(() => {
    if (!current) return;

    const tryMeasure = () => {
      const el = document.querySelector(current.target);
      if (!el) return false;

      const rect = el.getBoundingClientRect();

      // Only scroll if element is significantly off-screen
      const isAbove = rect.bottom < 80;
      const isBelow = rect.top > window.innerHeight - 120;

      if (isAbove || isBelow) {
        el.scrollIntoView({ behavior: 'instant', block: 'center' });
        const r2 = el.getBoundingClientRect();
        setTargetRect({ top: r2.top, left: r2.left, width: r2.width, height: r2.height });
      } else {
        setTargetRect({ top: rect.top, left: rect.left, width: rect.width, height: rect.height });
      }
      return true;
    };

    if (!tryMeasure()) {
      timerRef.current = setTimeout(() => {
        if (!tryMeasure()) {
          timerRef.current = setTimeout(tryMeasure, 500);
        }
      }, 400);
    }
  }, [current]);

  /* ── Step changes ────────────────────────────────────────────── */
  useEffect(() => {
    if (!isOpen || !current) return;
    clearTimeout(timerRef.current);

    if (location.pathname !== current.page) {
      setTargetRect(null);
      navigate(current.page);
      timerRef.current = setTimeout(measureTarget, 450);
    } else {
      measureTarget();
    }

    return () => clearTimeout(timerRef.current);
  }, [isOpen, step]);

  /* ── Navigation ──────────────────────────────────────────────── */
  const goNext = () => {
    if (isLast) return handleClose();
    setTargetRect(null);
    setStep(s => s + 1);
  };

  const goPrev = () => {
    if (isFirst) return;
    setTargetRect(null);
    setStep(s => s - 1);
  };

  const handleClose = () => {
    clearTimeout(timerRef.current);
    localStorage.setItem(LS_KEY, 'true');
    setStep(0);
    setTargetRect(null);
    onClose();
  };

  // Keyboard
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e) => {
      if (e.key === 'Escape') handleClose();
      if (e.key === 'ArrowRight') goNext();
      if (e.key === 'ArrowLeft') goPrev();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [isOpen, step]);

  if (!isOpen || !current) return null;

  /* ── Calculate tooltip + arrow position ──────────────────────── */
  const layout = computeLayout(targetRect, current.position || 'bottom');

  return (
    <div className="tour-overlay">
      {/* Dark mask with spotlight cutout */}
      {targetRect ? (
        <svg className="tour-mask" viewBox={`0 0 ${window.innerWidth} ${window.innerHeight}`}
          preserveAspectRatio="none">
          <defs>
            <mask id="tour-spotlight">
              <rect width="100%" height="100%" fill="white" />
              <rect
                x={targetRect.left - 8}
                y={targetRect.top - 8}
                width={targetRect.width + 16}
                height={targetRect.height + 16}
                rx="12"
                fill="black"
              />
            </mask>
          </defs>
          <rect width="100%" height="100%" fill="rgba(15, 23, 42, 0.6)" mask="url(#tour-spotlight)" />
        </svg>
      ) : (
        <div className="tour-mask-fallback" />
      )}

      {/* Spotlight ring */}
      {targetRect && (
        <div className="tour-spotlight-ring" style={{
          top: targetRect.top - 8,
          left: targetRect.left - 8,
          width: targetRect.width + 16,
          height: targetRect.height + 16,
        }} />
      )}

      {/* Speech bubble tooltip */}
      <div className="tour-tooltip" style={layout.tooltip}>
        {/* Dynamic arrow that points at the target */}
        <div className="tour-arrow" style={layout.arrow} />

        <button className="tour-close" onClick={handleClose} aria-label="Close tour">
          <HiOutlineX />
        </button>

        <div className="tour-step-counter">
          <span className="tour-step-num">{step + 1}</span>
          <span className="tour-step-sep">/</span>
          <span className="tour-step-total">{total}</span>
        </div>

        <h3 className="tour-title">{current.title}</h3>
        <p className="tour-desc">{current.description}</p>

        <div className="tour-dots">
          {TOUR_STEPS.map((_, i) => (
            <span key={i} className={`tour-dot ${i === step ? 'active' : i < step ? 'done' : ''}`} />
          ))}
        </div>

        <div className="tour-nav">
          <button className="tour-skip-btn" onClick={handleClose}>Skip Tour</button>
          <div className="tour-nav-btns">
            {!isFirst && (
              <button className="tour-prev-btn" onClick={goPrev}>
                <HiOutlineArrowLeft /> Back
              </button>
            )}
            <button className="tour-next-btn" onClick={goNext}>
              {isLast ? <><HiOutlineCheck /> Finish</> : <>Next <HiOutlineArrowRight /></>}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   LAYOUT CALCULATOR — positions tooltip + arrow relative to target
   ═══════════════════════════════════════════════════════════════════ */
function computeLayout(targetRect, position) {
  const fallback = {
    tooltip: { top: '50%', left: '50%', transform: 'translate(-50%, -50%)' },
    arrow: { display: 'none' },
  };

  if (!targetRect) return fallback;

  const pad = 18;
  const tw = 380;  // tooltip width
  const th = 260;  // tooltip approx height
  const vw = window.innerWidth;
  const vh = window.innerHeight;

  // Target center
  const tcx = targetRect.left + targetRect.width / 2;
  const tcy = targetRect.top + targetRect.height / 2;

  let ttop, tleft;
  const arrowStyle = {
    position: 'absolute', width: 14, height: 14, background: '#FFFFFF',
    border: '1px solid var(--border-default)', transform: 'rotate(45deg)', zIndex: -1
  };

  if (position === 'bottom') {
    ttop = targetRect.top + targetRect.height + pad;
    tleft = Math.max(16, Math.min(tcx - tw / 2, vw - tw - 16));
    ttop = Math.min(ttop, vh - th - 100);

    // Arrow: top edge, horizontally aligned to target center
    const arrowLeft = Math.max(20, Math.min(tcx - tleft - 7, tw - 30));
    Object.assign(arrowStyle, { top: -8, left: arrowLeft, borderRight: 'none', borderBottom: 'none' });

  } else if (position === 'top') {
    ttop = targetRect.top - th - pad;
    tleft = Math.max(16, Math.min(tcx - tw / 2, vw - tw - 16));
    ttop = Math.max(16, ttop);

    const arrowLeft = Math.max(20, Math.min(tcx - tleft - 7, tw - 30));
    Object.assign(arrowStyle, { bottom: -8, left: arrowLeft, borderLeft: 'none', borderTop: 'none' });

  } else if (position === 'right') {
    tleft = targetRect.left + targetRect.width + pad;
    ttop = Math.max(16, Math.min(tcy - th / 2, vh - th - 100));
    tleft = Math.min(tleft, vw - tw - 16);

    // Arrow: left edge, vertically aligned to target center
    const arrowTop = Math.max(20, Math.min(tcy - ttop - 7, th - 30));
    Object.assign(arrowStyle, { left: -8, top: arrowTop, borderRight: 'none', borderTop: 'none' });

  } else if (position === 'left') {
    tleft = targetRect.left - tw - pad;
    ttop = Math.max(16, Math.min(tcy - th / 2, vh - th - 100));
    tleft = Math.max(16, tleft);

    const arrowTop = Math.max(20, Math.min(tcy - ttop - 7, th - 30));
    Object.assign(arrowStyle, { right: -8, top: arrowTop, borderLeft: 'none', borderBottom: 'none' });
  }

  return {
    tooltip: { top: ttop, left: tleft },
    arrow: arrowStyle,
  };
}

export function hasTourBeenSeen() {
  return localStorage.getItem(LS_KEY) === 'true';
}
