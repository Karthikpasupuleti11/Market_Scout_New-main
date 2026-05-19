import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, NavLink, Link, useLocation } from 'react-router-dom';
import { HiOutlineBell, HiOutlineInformationCircle, HiMenu, HiX } from 'react-icons/hi';
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


function TopBar({ onStartTour, onToggleSidebar, sidebarOpen }) {
  return (
    <div className="topbar">
      <button
        className="topbar-hamburger"
        onClick={onToggleSidebar}
        aria-label={sidebarOpen ? 'Close menu' : 'Open menu'}
        aria-expanded={sidebarOpen}
      >
        {sidebarOpen ? <HiX /> : <HiMenu />}
      </button>
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
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    if (!hasTourBeenSeen()) {
      const timer = setTimeout(() => setTourOpen(true), 800);
      return () => clearTimeout(timer);
    }
  }, []);

  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname]);

  return (
    <div className={`app-layout ${sidebarOpen ? 'sidebar-open' : ''}`}>
      <TopBar
        onStartTour={() => setTourOpen(true)}
        onToggleSidebar={() => setSidebarOpen(v => !v)}
        sidebarOpen={sidebarOpen}
      />
      <div className="app-body">
        <Sidebar mobileOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
        {sidebarOpen && (
          <div
            className="sidebar-backdrop"
            onClick={() => setSidebarOpen(false)}
            aria-hidden="true"
          />
        )}
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