import { useState, useEffect, useRef } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
    HiOutlineGlobeAlt,
    HiOutlineLightningBolt,
    HiOutlineDocumentText,
    HiOutlineEye,
    HiOutlineClock,
    HiOutlineChartBar,
    HiOutlineCog,
    HiOutlineChatAlt2,
} from 'react-icons/hi';
import { SiPrometheus, SiGrafana } from 'react-icons/si';
import { getHealth } from '../api';
import SettingsPanel from './SettingsPanel';
import './Sidebar.css';

const PRIMARY_NAV = [
    { path: '/',            label: 'Overview',      icon: <HiOutlineGlobeAlt /> },
    { path: '/intelligence', label: 'Intelligence',  icon: <HiOutlineLightningBolt /> },
    { path: '/analysis',    label: 'Analysis',      icon: <HiOutlineChartBar /> },
    { path: '/reports',     label: 'Reports',       icon: <HiOutlineDocumentText /> },
    { path: '/watchlist',   label: 'Watchlist',     icon: <HiOutlineEye /> },
];

const SECONDARY_NAV = [
    { path: '/schedule', label: 'Automation', icon: <HiOutlineClock /> },
];

const FLOWER_URL = import.meta.env.VITE_FLOWER_URL || 'http://localhost:5555';

const EXTERNAL_LINKS = [
    { href: 'http://localhost:8000/docs',  label: 'API Docs',   icon: <HiOutlineChartBar /> },
    { href: 'http://localhost:9090',       label: 'Prometheus', icon: <SiPrometheus /> },
    { href: 'http://localhost:3000',       label: 'Grafana',    icon: <SiGrafana /> },
    { href: FLOWER_URL,                    label: 'Flower Tasks',     icon: <HiOutlineLightningBolt /> },
];

export default function Sidebar({ mobileOpen = false, onClose }) {
    const location = useLocation();
    const [settingsOpen, setSettingsOpen] = useState(false);
    const [backendUp, setBackendUp] = useState(true);
    const healthRef = useRef(null);

    // ── Live Health Polling (every 15s) ──────────────────────────
    useEffect(() => {
        const checkHealth = async () => {
            try {
                await getHealth();
                setBackendUp(true);
            } catch {
                setBackendUp(false);
            }
        };

        checkHealth(); // Immediate check

        healthRef.current = setInterval(checkHealth, 15000);

        return () => clearInterval(healthRef.current);
    }, []);

    return (
        <>
            <aside className={`sidebar ${mobileOpen ? 'mobile-open' : ''}`}>

                {/* ── Navigation ──────────────────────────────────── */}
                <nav className="sidebar-nav">

                    {/* Primary */}
                    <div className="nav-section">
                        <span className="nav-section-label">Intelligence</span>
                        {PRIMARY_NAV.map(item => (
                            <NavLink
                                key={item.path}
                                to={item.path}
                                className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                                end={item.path === '/'}
                            >
                                <span className="nav-icon">{item.icon}</span>
                                <span className="nav-label">{item.label}</span>
                                {item.path === location.pathname && <span className="nav-indicator" />}
                            </NavLink>
                        ))}
                    </div>

                    {/* Secondary */}
                    <div className="nav-section">
                        <span className="nav-section-label">System</span>
                        {SECONDARY_NAV.map(item => (
                            <NavLink
                                key={item.path}
                                to={item.path}
                                className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                            >
                                <span className="nav-icon">{item.icon}</span>
                                <span className="nav-label">{item.label}</span>
                                {item.path === location.pathname && <span className="nav-indicator" />}
                            </NavLink>
                        ))}
                    </div>

                    {/* External */}
                    <div className="nav-section">
                        <span className="nav-section-label">External</span>
                        {EXTERNAL_LINKS.map(link => (
                            <a key={link.href} href={link.href} target="_blank" rel="noopener noreferrer" className="nav-item external">
                                <span className="nav-icon">{link.icon}</span>
                                <span className="nav-label">{link.label}</span>
                                <span className="nav-external-badge">↗</span>
                            </a>
                        ))}
                    </div>
                </nav>

                {/* ── Settings Button ─────────────────────────────── */}
                <button
                    className={`sidebar-settings-btn ${settingsOpen ? 'active' : ''}`}
                    onClick={() => setSettingsOpen(true)}
                    aria-label="Open Settings"
                    id="settings-btn"
                >
                    <HiOutlineCog className="settings-gear-icon" />
                    <span>Settings</span>
                </button>

                {/* ── Footer ──────────────────────────────────────── */}
                <div className="sidebar-footer">
                    <div className="footer-status">
                        <span className={`status-dot ${backendUp ? 'online' : 'offline'}`} />
                        <span>{backendUp ? 'System Online' : 'Offline'}</span>
                    </div>
                    <div className="footer-badge">v2.0</div>
                </div>
            </aside>

            {/* Settings Drawer */}
            <SettingsPanel
                isOpen={settingsOpen}
                onClose={() => setSettingsOpen(false)}
            />
        </>
    );
}
