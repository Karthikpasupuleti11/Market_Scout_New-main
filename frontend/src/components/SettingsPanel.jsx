import { useState } from 'react';
import {
  HiOutlineX,
  HiOutlineRefresh,
  HiOutlineBeaker,
  HiOutlineEye,
  HiOutlineServer,
  HiOutlineTrash,
} from 'react-icons/hi';
import { useSettings } from '../contexts/SettingsContext';
import { clearCache, clearStorage } from '../api';
import './SettingsPanel.css';

export default function SettingsPanel({ isOpen, onClose }) {
  const {
    settings,
    updateAnalysis,
    updateWatchlist,
    resetToDefaults,
  } = useSettings();

  const handleClearCache = async () => {
    if (window.confirm("Are you sure you want to clear the Redis cache? This will temporarily slow down data retrieval.")) {
      try {
        await clearCache();
        alert("Cache cleared successfully!");
      } catch (err) {
        alert("Failed to clear cache: " + err.message);
      }
    }
  };

  const handleClearStorage = async () => {
    if (window.confirm("WARNING: This will permanently delete ALL companies, reports, and features from the database. Are you absolutely sure?")) {
      try {
        await clearStorage();
        alert("Database storage cleared successfully!");
        // We might want to reload the page to refresh all lists
        window.location.reload();
      } catch (err) {
        alert("Failed to clear storage: " + err.message);
      }
    }
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div className="settings-backdrop" onClick={onClose} />

      {/* Panel */}
      <div className="settings-panel">
        {/* Header */}
        <div className="settings-header">
          <div className="settings-title-group">
            <h2>Settings</h2>
            <span className="settings-subtitle">Customize your intelligence workflow</span>
          </div>
          <button className="settings-close-btn" onClick={onClose} aria-label="Close settings">
            <HiOutlineX />
          </button>
        </div>

        {/* Content */}
        <div className="settings-content">

          {/* ── 1. ANALYSIS ──────────────────────────────────────── */}
          <div className="settings-section fade-in">
            <div className="section-intro">
              <div className="section-intro-header">
                <div className="section-icon"><HiOutlineBeaker /></div>
                <h3>Analysis Configuration</h3>
              </div>
              <p>Controls how intelligence is generated and what signals are prioritized.</p>
            </div>

              {/* Time Window */}
              <div className="setting-group">
                <label className="setting-label">
                  <span className="setting-label-text">Time Window</span>
                  <span className="setting-hint">How far back to scan for intelligence signals</span>
                </label>
                <div className="setting-options-row">
                  {[
                    { value: 7, label: '7 days' },
                    { value: 14, label: '14 days' },
                    { value: 30, label: '30 days' },
                  ].map(opt => (
                    <button
                      key={opt.value}
                      className={`setting-chip ${settings.analysis.timeWindow === opt.value ? 'active' : ''}`}
                      onClick={() => updateAnalysis({ timeWindow: opt.value })}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="setting-group">
                <label className="setting-label">
                  <span className="setting-label-text">Force fresh analysis</span>
                  <span className="setting-hint">
                    Next run deletes that company&apos;s stored report (Redis + database,
                    within the 6-hour cache window) for the selected time window, then
                    runs a full new analysis
                  </span>
                </label>
                <div className="setting-options-row">
                  <button
                    type="button"
                    className={`setting-chip ${settings.analysis.forceRefresh ? 'active' : ''}`}
                    onClick={() => updateAnalysis({ forceRefresh: !settings.analysis.forceRefresh })}
                  >
                    {settings.analysis.forceRefresh ? 'On' : 'Off'}
                  </button>
                </div>
              </div>

              {/* Confidence Threshold */}
              <div className="setting-group">
                <label className="setting-label">
                  <span className="setting-label-text">Confidence Threshold</span>
                  <span className="setting-hint">Filter out signals below this confidence level</span>
                </label>
                <div className="setting-slider-row">
                  <input
                    type="range"
                    className="setting-slider"
                    min="50"
                    max="90"
                    step="5"
                    value={settings.analysis.confidenceThreshold}
                    onChange={e => updateAnalysis({ confidenceThreshold: Number(e.target.value) })}
                  />
                  <span className="setting-slider-value">{settings.analysis.confidenceThreshold}%</span>
                </div>
                <div className="slider-marks">
                  <span>50%</span>
                  <span>70%</span>
                  <span>90%</span>
                </div>
              </div>

          </div>

          <div className="settings-divider" />

          {/* ── 2. WATCHLIST ─────────────────────────────────────── */}
          <div className="settings-section fade-in" style={{ animationDelay: '0.1s' }}>
            <div className="section-intro">
              <div className="section-intro-header">
                <div className="section-icon"><HiOutlineEye /></div>
                <h3>Watchlist Behavior</h3>
              </div>
              <p>Configure how tracked companies are managed and displayed.</p>
            </div>



              {/* Default Sorting */}
              <div className="setting-group">
                <label className="setting-label">
                  <span className="setting-label-text">Default Sorting</span>
                  <span className="setting-hint">How companies are ordered in the watchlist</span>
                </label>
                <div className="setting-options-row">
                  {[
                    { value: 'recent', label: 'Recent Activity' },
                    { value: 'signal', label: 'Signal Strength' },
                    { value: 'confidence', label: 'Confidence' },
                  ].map(opt => (
                    <button
                      key={opt.value}
                      className={`setting-chip ${settings.watchlist.defaultSort === opt.value ? 'active' : ''}`}
                      onClick={() => updateWatchlist({ defaultSort: opt.value })}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

          </div>

          <div className="settings-divider" />

          {/* ── 3. DATA MANAGEMENT ───────────────────────────────── */}
          <div className="settings-section fade-in" style={{ animationDelay: '0.2s' }}>
            <div className="section-intro">
              <div className="section-intro-header">
                <div className="section-icon"><HiOutlineServer /></div>
                <h3>System & Data</h3>
              </div>
              <p>Manage application cache and database storage.</p>
            </div>

            <div className="setting-group">
              <label className="setting-label">
                <span className="setting-label-text">Clear Application Cache</span>
                <span className="setting-hint">Flushes Redis cache. Safe to do, but initial loads will be slower.</span>
              </label>
              <button 
                className="setting-action-btn"
                onClick={handleClearCache}
              >
                <HiOutlineRefresh /> Clear Cache
              </button>
            </div>

            <div className="setting-group">
              <label className="setting-label">
                <span className="setting-label-text danger-text">Clear All Storage</span>
                <span className="setting-hint">Permanently deletes all competitors, reports, and features from the database.</span>
              </label>
              <button 
                className="setting-action-btn danger-btn"
                onClick={handleClearStorage}
              >
                <HiOutlineTrash /> Clear Database
              </button>
            </div>
          </div>

        </div>

        {/* Footer */}
        <div className="settings-footer">
          <button className="btn btn-ghost settings-reset-btn" onClick={resetToDefaults}>
            <HiOutlineRefresh /> Reset to Defaults
          </button>
          <button className="btn btn-primary settings-done-btn" onClick={onClose}>
            Done
          </button>
        </div>
      </div>
    </>
  );
}
