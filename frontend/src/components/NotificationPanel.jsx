import { useState, useRef, useEffect } from 'react';
import { useNotifications } from '../contexts/NotificationContext';
import {
    HiOutlineBell,
    HiOutlineCheckCircle,
    HiOutlineXCircle,
    HiOutlineInformationCircle,
    HiOutlineExclamation,
    HiOutlineTrash,
    HiOutlineX,
} from 'react-icons/hi';
import './NotificationPanel.css';

const TYPE_CONFIG = {
    success: { icon: HiOutlineCheckCircle, color: 'var(--success)', label: 'Success' },
    error:   { icon: HiOutlineXCircle,     color: 'var(--error)',   label: 'Error' },
    info:    { icon: HiOutlineInformationCircle, color: 'var(--info)', label: 'Info' },
    warning: { icon: HiOutlineExclamation, color: 'var(--warning)', label: 'Warning' },
};

function timeAgo(dateStr) {
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
}

export default function NotificationPanel() {
    const { notifications, unreadCount, markAsRead, markAllRead, removeNotification, clearAll } = useNotifications();
    const [open, setOpen] = useState(false);
    const panelRef = useRef(null);

    // Close on outside click
    useEffect(() => {
        if (!open) return;
        function handleClick(e) {
            if (panelRef.current && !panelRef.current.contains(e.target)) {
                setOpen(false);
            }
        }
        document.addEventListener('mousedown', handleClick);
        return () => document.removeEventListener('mousedown', handleClick);
    }, [open]);

    const handleToggle = () => {
        setOpen(prev => !prev);
    };

    const handleNotificationClick = (n) => {
        if (!n.read) markAsRead(n.id);
    };

    return (
        <div className="notif-wrapper" ref={panelRef}>
            <button
                className={`topbar-bell ${open ? 'active' : ''}`}
                aria-label="Notifications"
                onClick={handleToggle}
            >
                <HiOutlineBell />
                {unreadCount > 0 && (
                    <span className="topbar-bell-badge">{unreadCount > 9 ? '9+' : unreadCount}</span>
                )}
            </button>

            {open && (
                <div className="notif-panel fade-in">
                    <div className="notif-header">
                        <h4>Notifications</h4>
                        <div className="notif-header-actions">
                            {unreadCount > 0 && (
                                <button className="notif-action-btn" onClick={markAllRead} title="Mark all read">
                                    <HiOutlineCheckCircle /> Read All
                                </button>
                            )}
                            {notifications.length > 0 && (
                                <button className="notif-action-btn danger" onClick={clearAll} title="Clear all">
                                    <HiOutlineTrash />
                                </button>
                            )}
                        </div>
                    </div>

                    <div className="notif-list">
                        {notifications.length === 0 ? (
                            <div className="notif-empty">
                                <HiOutlineBell className="notif-empty-icon" />
                                <p>No notifications yet</p>
                                <span>Pipeline completions and schedule updates will appear here</span>
                            </div>
                        ) : (
                            notifications.map(n => {
                                const cfg = TYPE_CONFIG[n.type] || TYPE_CONFIG.info;
                                const Icon = cfg.icon;
                                return (
                                    <div
                                        key={n.id}
                                        className={`notif-item ${n.read ? '' : 'unread'}`}
                                        onClick={() => handleNotificationClick(n)}
                                    >
                                        <div className="notif-icon" style={{ color: cfg.color }}>
                                            <Icon />
                                        </div>
                                        <div className="notif-content">
                                            <div className="notif-title">{n.title}</div>
                                            <div className="notif-message">{n.message}</div>
                                            <div className="notif-time">{timeAgo(n.timestamp)}</div>
                                        </div>
                                        <button
                                            className="notif-remove"
                                            onClick={(e) => { e.stopPropagation(); removeNotification(n.id); }}
                                            title="Dismiss"
                                        >
                                            <HiOutlineX />
                                        </button>
                                    </div>
                                );
                            })
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
