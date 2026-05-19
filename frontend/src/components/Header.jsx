import { useState, useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { getHealth } from '../api';
import './Header.css';

const PAGE_TITLES = {
    '/': 'Dashboard',
    '/run': 'Run Pipeline',
    '/reports': 'Reports',
    '/competitors': 'Competitors',
};

export default function Header() {
    const location = useLocation();
    const title = PAGE_TITLES[location.pathname] || 'Market Scout';
    const [backendUp, setBackendUp] = useState(null); // null = checking, true = up, false = down
    const intervalRef = useRef(null);

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

    const statusClass = backendUp === null ? 'checking' : backendUp ? 'connected' : 'disconnected';
    const statusLabel = backendUp === null ? 'Checking…' : backendUp ? 'Backend Connected' : 'Backend Offline';

    return (
        <header className="header">
            <div className="header-left">
                <h2 className="header-title">{title}</h2>
            </div>
            <div className="header-right">
                <div className={`header-status ${statusClass}`}>
                    <span className={`status-dot ${statusClass}`} />
                    <span className="status-text">{statusLabel}</span>
                </div>
            </div>
        </header>
    );
}
