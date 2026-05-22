import { useState, useRef, useEffect } from 'react';
import {
    HiOutlineBell,
    HiOutlineCheck,
    HiOutlineTrash,
    HiOutlineX,
    HiOutlineLightningBolt,
    HiOutlineClock,
    HiOutlineExclamationCircle,
    HiOutlineCheckCircle,
    HiOutlineInformationCircle,
} from 'react-icons/hi';
import { useNotifications } from '../contexts/NotificationsContext';
import './NotificationPanel.css';

/* ── Icon map by notification type ────────────────────────────── */
const TYPE_ICON = {
    success: <HiOutlineCheckCircle />,
    error:   <HiOutlineExclamationCircle />,
    warning: <HiOutlineExclamationCircle />,
    info:    <HiOutlineInformationCircle />,
    pipeline: <HiOutlineLightningBolt />,
    schedule: <HiOutlineClock />,
};

function formatTimeAgo(dateStr) {
    if (!dateStr) return '';
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins  = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days  = Math.floor(diff / 86400000);
    if (mins < 1)   return 'Just now';
    if (mins < 60)  return `${mins}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7)   return `${days}d ago`;
    return new Date(dateStr).toLocaleDateString([], { dateStyle: 'medium' });
}

export default function NotificationPanel({ open, onClose }) {
    const { notifications, unreadCount, markAllRead, markRead, clearAll, dismiss } = useNotifications();
    const panelRef = useRef(null);

    // Close on outside click
    useEffect(() => {
        if (!open) return;
        function handleClick(e) {
            if (panelRef.current && !panelRef.current.contains(e.target)) {
                onClose();
            }
        }
        // Delay to avoid immediate close from the toggle click
        const timer = setTimeout(() => {
            document.addEventListener('mousedown', handleClick);
        }, 10);
        return () => {
            clearTimeout(timer);
            document.removeEventListener('mousedown', handleClick);
        };
    }, [open, onClose]);

    // Remove automatic mark-all-read so user can manually mark them.

    if (!open) return null;

    return (
        <div className="notification-panel" ref={panelRef}>
            <div className="notif-header">
                <h3>Notifications</h3>
                <div className="notif-header-actions" style={{ display: 'flex', gap: '8px' }}>
                    {unreadCount > 0 && (
                        <button
                            className="notif-clear-btn"
                            onClick={markAllRead}
                            title="Mark all as read"
                        >
                            <HiOutlineCheck />
                            <span>Mark Read</span>
                        </button>
                    )}
                    {notifications.length > 0 && (
                        <button
                            className="notif-clear-btn"
                            onClick={clearAll}
                            title="Clear all"
                        >
                            <HiOutlineTrash />
                            <span>Clear</span>
                        </button>
                    )}
                </div>
            </div>

            {/* Body */}
            <div className="notif-body">
                {notifications.length === 0 ? (
                    <div className="notif-empty">
                        <HiOutlineBell className="notif-empty-icon" />
                        <p className="notif-empty-title">No notifications yet</p>
                        <p className="notif-empty-desc">
                            Pipeline completions and schedule updates will appear here
                        </p>
                    </div>
                ) : (
                    <div className="notif-list">
                        {notifications.map(n => (
                            <div
                                key={n.id}
                                className={`notif-item notif-${n.type} ${n.read ? '' : 'unread'}`}
                            >
                                <span className={`notif-icon notif-icon-${n.type}`}>
                                    {TYPE_ICON[n.type] || TYPE_ICON.info}
                                </span>
                                <div className="notif-content">
                                    <span className="notif-title">{n.title}</span>
                                    {n.message && (
                                        <span className="notif-message">{n.message}</span>
                                    )}
                                    <span className="notif-time">{formatTimeAgo(n.timestamp)}</span>
                                </div>
                                <div className="notif-actions" style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                                    {!n.read && (
                                        <button
                                            className="notif-dismiss"
                                            onClick={(e) => { e.stopPropagation(); markRead(n.id); }}
                                            title="Mark as read"
                                        >
                                            <HiOutlineCheck />
                                        </button>
                                    )}
                                    <button
                                        className="notif-dismiss"
                                        onClick={(e) => { e.stopPropagation(); dismiss(n.id); }}
                                        title="Dismiss"
                                    >
                                        <HiOutlineX />
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
