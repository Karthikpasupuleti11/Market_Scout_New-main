import { createContext, useContext, useState, useCallback, useEffect } from 'react';

/* ═══════════════════════════════════════════════════════════════════
   NOTIFICATION CONTEXT — App-wide notification system.
   Stores notifications in localStorage so they persist across refreshes.
   ═══════════════════════════════════════════════════════════════════ */

const STORAGE_KEY = 'ms_notifications';
const MAX_NOTIFICATIONS = 30;

const NotificationContext = createContext(null);

function loadFromStorage() {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        return raw ? JSON.parse(raw) : [];
    } catch {
        return [];
    }
}

function saveToStorage(notifications) {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(notifications.slice(0, MAX_NOTIFICATIONS)));
    } catch { /* ignore quota errors */ }
}

export function NotificationProvider({ children }) {
    const [notifications, setNotifications] = useState(() => loadFromStorage());

    // Sync to localStorage on change
    useEffect(() => {
        saveToStorage(notifications);
    }, [notifications]);

    /**
     * Add a new notification.
     * @param {'success'|'error'|'info'|'warning'} type
     * @param {string} title
     * @param {string} message
     */
    const addNotification = useCallback((type, title, message) => {
        const notification = {
            id: Date.now() + Math.random().toString(36).slice(2, 6),
            type,
            title,
            message,
            timestamp: new Date().toISOString(),
            read: false,
        };
        setNotifications(prev => [notification, ...prev].slice(0, MAX_NOTIFICATIONS));
    }, []);

    const markAsRead = useCallback((id) => {
        setNotifications(prev =>
            prev.map(n => n.id === id ? { ...n, read: true } : n)
        );
    }, []);

    const markAllRead = useCallback(() => {
        setNotifications(prev => prev.map(n => ({ ...n, read: true })));
    }, []);

    const removeNotification = useCallback((id) => {
        setNotifications(prev => prev.filter(n => n.id !== id));
    }, []);

    const clearAll = useCallback(() => {
        setNotifications([]);
    }, []);

    const unreadCount = notifications.filter(n => !n.read).length;

    return (
        <NotificationContext.Provider value={{
            notifications,
            unreadCount,
            addNotification,
            markAsRead,
            markAllRead,
            removeNotification,
            clearAll,
        }}>
            {children}
        </NotificationContext.Provider>
    );
}

export function useNotifications() {
    const ctx = useContext(NotificationContext);
    if (!ctx) throw new Error('useNotifications must be inside <NotificationProvider>');
    return ctx;
}
