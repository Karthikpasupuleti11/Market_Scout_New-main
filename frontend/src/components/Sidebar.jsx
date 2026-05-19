import { useState, useEffect, useRef, useCallback } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
    HiOutlineGlobeAlt,
    HiOutlineLightningBolt,
    HiOutlineDocumentText,
    HiOutlineEye,
    HiOutlineClock,
    HiOutlineChartBar,
    HiOutlineCog,
    HiOutlineMenu,
    HiOutlineX,
} from 'react-icons/hi';
import { SiPrometheus, SiGrafana } from 'react-icons/si';
import { getHealth } from '../api';
import { DOCS_URL, PROMETHEUS_URL, GRAFANA_URL, FLOWER_URL } from '../config/urls';
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

const EXTERNAL_LINKS = [
    { href: DOCS_URL, label: 'API Docs', icon: <HiOutlineChartBar /> },
    { href: PROMETHEUS_URL, label: 'Prometheus', icon: <SiPrometheus /> },
    { href: GRAFANA_URL, label: 'Grafana', icon: <SiGrafana /> },
    { href: FLOWER_URL, label: 'Flower Tasks', icon: <HiOutlineLightningBolt /> },
];

export default function Sidebar({ mobileOpen = false, onClose }) {
    const location = useLocation();
    const [settingsOpen, setSettingsOpen] = useState(false);
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [backendUp, setBackendUp] = useState(null); // null = checking, true = up, false = down
    const intervalRef = useRef(null);

    // Close sidebar on route change (mobile)
    useEffect(() => {
        setSidebarOpen(false);
    }, [location.pathname]);

    const toggleSidebar = useCallback(() => setSidebarOpen(prev => !prev), []);

    useEffect(() => {
        async function check() {
            try {
                await getHealth();
                setBackendUp(true);
            } catch {
                setBackendUp(false);
            }
        }
        check();
        intervalRef.current = setInterval(check, 15000);
        return () => clearInterval(intervalRef.current);
    }, []);

    const statusLabel = backendUp === null ? 'Checking…' : backendUp ? 'System Online' : 'System Offline';
    const statusClass = backendUp === null ? 'checking' : backendUp ? 'online' : 'offline';

    return (
        <>
            {/* Hamburger button — visible on mobile only */}
            <button
                className="sidebar-hamburger"
                onClick={toggleSidebar}
                aria-label={sidebarOpen ? 'Close menu' : 'Open menu'}
            >
                {sidebarOpen ? <HiOutlineX /> : <HiOutlineMenu />}
            </button>

            {/* Backdrop — visible on mobile when sidebar open */}
            {sidebarOpen && (
                <div
                    className="sidebar-backdrop visible"
                    onClick={() => setSidebarOpen(false)}
                />
            )}

            <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>

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
                    <div className={`footer-status ${statusClass}`}>
                        <span className={`status-dot ${statusClass}`} />
                        <span>{statusLabel}</span>
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

