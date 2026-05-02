import { useState } from 'react';
import {
  HiOutlineX,
  HiOutlineBeaker,
  HiOutlineDocumentText,
  HiOutlineEye,
  HiOutlineUser,
  HiOutlineRefresh,
  HiOutlineClock,
  HiOutlineShieldCheck,
  HiOutlineChip,
  HiOutlineCode,
  HiOutlineServer,
  HiOutlineInformationCircle,
} from 'react-icons/hi';
import { useSettings } from '../contexts/SettingsContext';
import './SettingsPanel.css';

const TABS = [
  { id: 'analysis', label: 'Analysis', icon: <HiOutlineBeaker /> },
  { id: 'reports', label: 'Reports', icon: <HiOutlineDocumentText /> },
  { id: 'watchlist', label: 'Watchlist', icon: <HiOutlineEye /> },
  { id: 'profile', label: 'Profile & UI', icon: <HiOutlineUser /> },
];

export default function SettingsPanel({ isOpen, onClose }) {
  const [activeTab, setActiveTab] = useState('analysis');
  const {
    settings,
    updateAnalysis,
    updateReports,
    updateWatchlist,
    updateProfile,
    toggleCategory,
    resetToDefaults,
  } = useSettings();

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

        {/* Tab navigation */}
        <div className="settings-tabs">
          {TABS.map(tab => (
            <button
              key={tab.id}
              className={`settings-tab ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              <span className="settings-tab-icon">{tab.icon}</span>
              <span>{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="settings-content">

          {/* ── 1. ANALYSIS ──────────────────────────────────────── */}
          {activeTab === 'analysis' && (
            <div className="settings-section fade-in">
              <div className="section-intro">
                <h3>Analysis Configuration</h3>
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

              {/* Source Depth */}
              <div className="setting-group">
                <label className="setting-label">
                  <span className="setting-label-text">Source Depth</span>
                  <span className="setting-hint">How many sources to analyze per query</span>
                </label>
                <div className="setting-options-row">
                  {[
                    { value: 'light', label: 'Light', desc: 'Fast scan' },
                    { value: 'balanced', label: 'Balanced', desc: 'Recommended' },
                    { value: 'deep', label: 'Deep', desc: 'Thorough' },
                  ].map(opt => (
                    <button
                      key={opt.value}
                      className={`setting-chip depth-chip ${settings.analysis.sourceDepth === opt.value ? 'active' : ''}`}
                      onClick={() => updateAnalysis({ sourceDepth: opt.value })}
                    >
                      <span>{opt.label}</span>
                      <span className="chip-desc">{opt.desc}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Default Categories */}
              <div className="setting-group">
                <label className="setting-label">
                  <span className="setting-label-text">Default Categories</span>
                  <span className="setting-hint">Bias the analysis towards these areas</span>
                </label>
                <div className="category-toggles">
                  {[
                    { key: 'ai', label: 'AI', icon: <HiOutlineChip /> },
                    { key: 'infrastructure', label: 'Infrastructure', icon: <HiOutlineServer /> },
                    { key: 'security', label: 'Security', icon: <HiOutlineShieldCheck /> },
                    { key: 'developer', label: 'Developer', icon: <HiOutlineCode /> },
                  ].map(cat => (
                    <button
                      key={cat.key}
                      className={`category-toggle ${settings.analysis.defaultCategories[cat.key] ? 'active' : ''}`}
                      onClick={() => toggleCategory(cat.key)}
                    >
                      <span className="cat-icon">{cat.icon}</span>
                      <span className="cat-label">{cat.label}</span>
                      <span className={`cat-indicator ${settings.analysis.defaultCategories[cat.key] ? 'on' : 'off'}`}>
                        {settings.analysis.defaultCategories[cat.key] ? 'ON' : 'OFF'}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ── 2. REPORTS ───────────────────────────────────────── */}
          {activeTab === 'reports' && (
            <div className="settings-section fade-in">
              <div className="section-intro">
                <h3>Report Preferences</h3>
                <p>Controls how intelligence results are presented and exported.</p>
              </div>

              {/* Detail Level */}
              <div className="setting-group">
                <label className="setting-label">
                  <span className="setting-label-text">Report Detail Level</span>
                  <span className="setting-hint">Amount of detail included in generated reports</span>
                </label>
                <div className="setting-options-row">
                  {[
                    { value: 'compact', label: 'Compact', desc: 'Executive summary' },
                    { value: 'detailed', label: 'Detailed', desc: 'Full analyst view' },
                  ].map(opt => (
                    <button
                      key={opt.value}
                      className={`setting-chip depth-chip ${settings.reports.detailLevel === opt.value ? 'active' : ''}`}
                      onClick={() => updateReports({ detailLevel: opt.value })}
                    >
                      <span>{opt.label}</span>
                      <span className="chip-desc">{opt.desc}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Include Sources */}
              <div className="setting-group">
                <label className="setting-label">
                  <span className="setting-label-text">Include Sources</span>
                  <span className="setting-hint">Attach source links to reports and exports</span>
                </label>
                <div className="setting-toggle-row">
                  <button
                    className={`toggle-switch ${settings.reports.includeSources ? 'on' : 'off'}`}
                    onClick={() => updateReports({ includeSources: !settings.reports.includeSources })}
                    role="switch"
                    aria-checked={settings.reports.includeSources}
                  >
                    <span className="toggle-knob" />
                  </button>
                  <span className="toggle-label">
                    {settings.reports.includeSources ? 'Sources will be included' : 'Sources hidden from reports'}
                  </span>
                </div>
              </div>

              {/* Export Format */}
              <div className="setting-group">
                <label className="setting-label">
                  <span className="setting-label-text">Default Export Format</span>
                  <span className="setting-hint">File format for downloaded reports</span>
                </label>
                <div className="setting-options-row">
                  <button
                    className={`setting-chip ${settings.reports.exportFormat === 'pdf' ? 'active' : ''}`}
                    onClick={() => updateReports({ exportFormat: 'pdf' })}
                  >
                    PDF
                  </button>
                  <button className="setting-chip disabled" disabled title="Coming soon">
                    JSON <span className="coming-soon">Soon</span>
                  </button>
                  <button className="setting-chip disabled" disabled title="Coming soon">
                    CSV <span className="coming-soon">Soon</span>
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* ── 3. WATCHLIST ─────────────────────────────────────── */}
          {activeTab === 'watchlist' && (
            <div className="settings-section fade-in">
              <div className="section-intro">
                <h3>Watchlist Behavior</h3>
                <p>Configure how tracked companies are managed and displayed.</p>
              </div>

              {/* Auto-add */}
              <div className="setting-group">
                <label className="setting-label">
                  <span className="setting-label-text">Auto-add Analyzed Companies</span>
                  <span className="setting-hint">Automatically track companies after running analysis</span>
                </label>
                <div className="setting-toggle-row">
                  <button
                    className={`toggle-switch ${settings.watchlist.autoAdd ? 'on' : 'off'}`}
                    onClick={() => updateWatchlist({ autoAdd: !settings.watchlist.autoAdd })}
                    role="switch"
                    aria-checked={settings.watchlist.autoAdd}
                  >
                    <span className="toggle-knob" />
                  </button>
                  <span className="toggle-label">
                    {settings.watchlist.autoAdd ? 'Companies auto-added to watchlist' : 'Manual tracking only'}
                  </span>
                </div>
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

              {/* Highlight Rule */}
              <div className="setting-group">
                <label className="setting-label">
                  <span className="setting-label-text">Highlight High-Confidence Only</span>
                  <span className="setting-hint">Dim low-confidence companies in the watchlist</span>
                </label>
                <div className="setting-toggle-row">
                  <button
                    className={`toggle-switch ${settings.watchlist.highlightHighConfidence ? 'on' : 'off'}`}
                    onClick={() => updateWatchlist({ highlightHighConfidence: !settings.watchlist.highlightHighConfidence })}
                    role="switch"
                    aria-checked={settings.watchlist.highlightHighConfidence}
                  >
                    <span className="toggle-knob" />
                  </button>
                  <span className="toggle-label">
                    {settings.watchlist.highlightHighConfidence
                      ? 'Only high-confidence companies highlighted'
                      : 'All companies shown equally'}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* ── 4. PROFILE & UI (non-functional) ─────────────────── */}
          {activeTab === 'profile' && (
            <div className="settings-section fade-in">
              <div className="section-intro">
                <h3>Profile & Experience</h3>
                <p>Personal preferences and display settings.</p>
              </div>

              {/* Name */}
              <div className="setting-group">
                <label className="setting-label">
                  <span className="setting-label-text">Display Name</span>
                </label>
                <input
                  type="text"
                  className="setting-input"
                  value={settings.profile.name}
                  onChange={e => updateProfile({ name: e.target.value })}
                  placeholder="Your name"
                />
              </div>

              {/* Email */}
              <div className="setting-group">
                <label className="setting-label">
                  <span className="setting-label-text">Email Address</span>
                </label>
                <input
                  type="email"
                  className="setting-input"
                  value={settings.profile.email}
                  onChange={e => updateProfile({ email: e.target.value })}
                  placeholder="your@email.com"
                />
              </div>

              {/* Theme */}
              <div className="setting-group">
                <label className="setting-label">
                  <span className="setting-label-text">Theme</span>
                  <span className="setting-hint">Visual appearance of the interface</span>
                </label>
                <div className="setting-options-row">
                  <button
                    className={`setting-chip ${settings.profile.theme === 'light' ? 'active' : ''}`}
                    onClick={() => updateProfile({ theme: 'light' })}
                  >
                    Light
                  </button>
                  <button className="setting-chip disabled" disabled title="Coming soon">
                    Dark <span className="coming-soon">Soon</span>
                  </button>
                  <button className="setting-chip disabled" disabled title="Coming soon">
                    Auto <span className="coming-soon">Soon</span>
                  </button>
                </div>
              </div>

              {/* Density */}
              <div className="setting-group">
                <label className="setting-label">
                  <span className="setting-label-text">Density</span>
                  <span className="setting-hint">Spacing and compactness of the interface</span>
                </label>
                <div className="setting-options-row">
                  {[
                    { value: 'comfortable', label: 'Comfortable' },
                    { value: 'compact', label: 'Compact' },
                  ].map(opt => (
                    <button
                      key={opt.value}
                      className={`setting-chip ${settings.profile.density === opt.value ? 'active' : ''}`}
                      onClick={() => updateProfile({ density: opt.value })}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="profile-note">
                <HiOutlineInformationCircle className="profile-note-icon" />
                <span>Theme and density changes will be available in a future update.</span>
              </div>
            </div>
          )}
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
