import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, NavLink, Link, Navigate } from 'react-router-dom';
import { HiOutlineInformationCircle, HiOutlineQuestionMarkCircle } from 'react-icons/hi';
import { SettingsProvider } from './contexts/SettingsContext';
import { PipelineProvider } from './contexts/PipelineContext';
import { NotificationProvider } from './contexts/NotificationContext';
import NotificationPanel from './components/NotificationPanel';
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
          className="topbar-link"
          onClick={onStartTour}
          title="Take a guided tour"
          aria-label="Start guided tour"
        >
          <HiOutlineQuestionMarkCircle />
          <span>Tour</span>
        </button>
        <NotificationPanel />
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
            <Route path="*" element={<Navigate to="/" replace />} />
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
      <NotificationProvider>
        <PipelineProvider>
          <BrowserRouter>
            <AppContent />
          </BrowserRouter>
        </PipelineProvider>
      </NotificationProvider>
    </SettingsProvider>
  );
}