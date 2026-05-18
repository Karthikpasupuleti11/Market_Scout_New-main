import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, NavLink, Link } from 'react-router-dom';
import { HiOutlineBell, HiOutlineInformationCircle } from 'react-icons/hi';
import { SettingsProvider } from './contexts/SettingsContext';
import { PipelineProvider } from './contexts/PipelineContext';   // ← NEW
import Sidebar from './components/Sidebar';
import GuidedTour, { hasTourBeenSeen } from './components/GuidedTour';
import Dashboard from './pages/Dashboard';
import RunPipeline from './pages/RunPipeline';
import Analysis from './pages/Analysis';
import Reports from './pages/Reports';
import Competitors from './pages/Competitors';
import Schedule from './pages/Schedule';
import About from './pages/About';


function TopBar({ onStartTour }) {
  return (
    <div className="topbar">
      <Link to="/" className="topbar-brand" aria-label="Go to Overview">
        <img src="/assets/logo.png" alt="Market Scout" className="topbar-logo" />
        <div className="topbar-brand-text">
          <h1>Market Scout</h1>
          <span>Intelligence Platform</span>
        </div>
      </Link>
      <div className="topbar-actions">
        <NavLink
          to="/about"
          className={({ isActive }) => `topbar-link ${isActive ? 'active' : ''}`}
        >
          <HiOutlineInformationCircle />
          <span>About Us</span>
        </NavLink>
        <button
          className="tour-help-btn"
          onClick={onStartTour}
          title="Take a guided tour"
          aria-label="Start guided tour"
        >
          ?
        </button>
        <button className="topbar-bell" aria-label="Notifications">
          <HiOutlineBell />
          <span className="topbar-bell-dot" />
        </button>
        <div className="topbar-avatar" title="User">
          <span>U</span>
        </div>
      </div>
    </div>
  );
}

function AppContent() {
  const [tourOpen, setTourOpen] = useState(false);

  useEffect(() => {
    if (!hasTourBeenSeen()) {
      const timer = setTimeout(() => setTourOpen(true), 800);
      return () => clearTimeout(timer);
    }
  }, []);

  return (
    <div className="app-layout">
      <TopBar onStartTour={() => setTourOpen(true)} />
      <div className="app-body">
        <Sidebar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/intelligence" element={<RunPipeline />} />
            <Route path="/analysis" element={<Analysis />} />
            <Route path="/schedule" element={<Schedule />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/watchlist" element={<Competitors />} />
            <Route path="/about" element={<About />} />
            <Route path="/run" element={<RunPipeline />} />
            <Route path="/competitors" element={<Competitors />} />
          </Routes>
        </main>
      </div>

      <GuidedTour
        isOpen={tourOpen}
        onClose={() => setTourOpen(false)}
      />
    </div>
  );
}

export default function App() {
  return (
    <SettingsProvider>
      {/* PipelineProvider sits OUTSIDE BrowserRouter so state survives
          route changes — the fetch + timers live here, not in the page */}
      <PipelineProvider>
        <BrowserRouter>
          <AppContent />
        </BrowserRouter>
      </PipelineProvider>
    </SettingsProvider>
  );
}