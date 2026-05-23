import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, NavLink, Link, useLocation } from 'react-router-dom';
import { HiOutlineBell, HiOutlineInformationCircle, HiOutlineQuestionMarkCircle, HiMenu, HiX } from 'react-icons/hi';
import { SettingsProvider } from './contexts/SettingsContext';
import { PipelineProvider } from './contexts/PipelineContext';
import { NotificationsProvider, useNotifications } from './contexts/NotificationsContext';
import Sidebar from './components/Sidebar';
import NotificationPanel from './components/NotificationPanel';
import GuidedTour, { hasTourBeenSeen } from './components/GuidedTour';
import Dashboard from './pages/Dashboard';
import RunPipeline from './pages/RunPipeline';
import Analysis from './pages/Analysis';
import Reports from './pages/Reports';
import FeedbackWidget from './components/FeedbackWidget';
import Competitors from './pages/Competitors';
import Schedule from './pages/Schedule';
import About from './pages/About';


function TopBar({ onStartTour, onToggleSidebar, sidebarOpen }) {
  const [notifOpen, setNotifOpen] = useState(false);
  const { unreadCount } = useNotifications();

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
          className="topbar-link"
          onClick={onStartTour}
          aria-label="Start guided tour"
        >
          <HiOutlineQuestionMarkCircle />
          <span>Tour</span>
        </button>
        <div className="topbar-notif-wrapper">
          <button
            className={`topbar-link ${notifOpen ? 'active' : ''}`}
            onClick={() => setNotifOpen(v => !v)}
            aria-label="Notifications"
            id="notifications-btn"
          >
            <HiOutlineBell />
            <span>Notifications</span>
            {unreadCount > 0 && (
              <span className="topbar-notif-badge">{unreadCount > 9 ? '9+' : unreadCount}</span>
            )}
          </button>
          <NotificationPanel
            open={notifOpen}
            onClose={() => setNotifOpen(false)}
          />
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
      <FeedbackWidget />
    </div>
  );
}

export default function App() {
  return (
    <SettingsProvider>
      <NotificationsProvider>
        <PipelineProvider>
          <BrowserRouter>
            <AppContent />
          </BrowserRouter>
        </PipelineProvider>
      </NotificationsProvider>
    </SettingsProvider>
  );
}