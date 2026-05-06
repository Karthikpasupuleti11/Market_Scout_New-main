import { createContext, useContext, useState, useEffect, useCallback } from 'react';

/* ═══════════════════════════════════════════════════════════════════
   SETTINGS CONTEXT — Persistent application settings
   Sections: Analysis · Reports · Watchlist · Profile & UI
   ═══════════════════════════════════════════════════════════════════ */

const STORAGE_KEY = 'market_scout_settings';

const DEFAULT_SETTINGS = {
  // ── 1. Analysis ─────────────────────────────────────────────────
  analysis: {
    timeWindow: 7,              // 7 | 14 | 30 days
    confidenceThreshold: 50,    // 50–90 slider (percentage)
  },

  // ── 2. Watchlist ────────────────────────────────────────────────
  watchlist: {
    defaultSort: 'recent',      // 'recent' | 'signal' | 'confidence'
  },
};

const SettingsContext = createContext(null);

export function SettingsProvider({ children }) {
  const [settings, setSettings] = useState(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        // Deep merge with defaults so new keys are always present
        return deepMerge(DEFAULT_SETTINGS, parsed);
      }
    } catch { /* ignore corrupt data */ }
    return DEFAULT_SETTINGS;
  });

  // Persist on every change
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  }, [settings]);

  const updateSection = useCallback((section, patch) => {
    setSettings(prev => ({
      ...prev,
      [section]: { ...prev[section], ...patch },
    }));
  }, []);

  const updateAnalysis = useCallback((patch) => updateSection('analysis', patch), [updateSection]);
  const updateWatchlist = useCallback((patch) => updateSection('watchlist', patch), [updateSection]);

  const resetToDefaults = useCallback(() => {
    setSettings(DEFAULT_SETTINGS);
  }, []);

  return (
    <SettingsContext.Provider value={{
      settings,
      updateAnalysis,
      updateWatchlist,
      resetToDefaults,
    }}>
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettings() {
  const ctx = useContext(SettingsContext);
  if (!ctx) throw new Error('useSettings must be inside <SettingsProvider>');
  return ctx;
}

/* ── Utility: deep merge objects ─────────────────────────────────── */
function deepMerge(defaults, overrides) {
  const result = { ...defaults };
  for (const key of Object.keys(defaults)) {
    if (
      overrides[key] !== undefined &&
      typeof defaults[key] === 'object' &&
      !Array.isArray(defaults[key]) &&
      defaults[key] !== null
    ) {
      result[key] = deepMerge(defaults[key], overrides[key]);
    } else if (overrides[key] !== undefined) {
      result[key] = overrides[key];
    }
  }
  return result;
}
