import { createContext, useContext, useState, useCallback, useEffect } from 'react';

/* ═══════════════════════════════════════════════════════════════════
   NOTIFICATIONS CONTEXT — Stores and manages app notifications
   Persists to localStorage so they survive page refreshes.
   ═══════════════════════════════════════════════════════════════════ */

const STORAGE_KEY = 'market_scout_notifications';
const MAX_NOTIFICATIONS = 50;

const NotificationsContext = createContext(null);

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
        localStorage.setItem(STORAGE_KEY, JSON.stringify(notifications));
    } catch { /* quota exceeded — silently ignore */ }
}

export function NotificationsProvider({ children }) {
    const [notifications, setNotifications] = useState(loadFromStorage);
    const [unreadCount, setUnreadCount] = useState(0);

    // Recalculate unread count whenever notifications change
    useEffect(() => {
        const count = notifications.filter(n => !n.read).length;
        setUnreadCount(count);
        saveToStorage(notifications);
    }, [notifications]);

    // Push a new notification
    const pushNotification = useCallback(({ type = 'info', title, message }) => {
        const notification = {
            id: `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
            type,       // 'success' | 'error' | 'info' | 'warning'
            title,
            message,
            read: false,
            timestamp: new Date().toISOString(),
        };

        setNotifications(prev => {
            const updated = [notification, ...prev].slice(0, MAX_NOTIFICATIONS);
            return updated;
        });
    }, []);

    // Mark all as read
    const markAllRead = useCallback(() => {
        setNotifications(prev =>
            prev.map(n => ({ ...n, read: true }))
        );
    }, []);

    // Mark one as read
    const markRead = useCallback((id) => {
        setNotifications(prev =>
            prev.map(n => (n.id === id ? { ...n, read: true } : n))
        );
    }, []);

    // Clear all
    const clearAll = useCallback(() => {
        setNotifications([]);
    }, []);

    // Dismiss one
    const dismiss = useCallback((id) => {
        setNotifications(prev => prev.filter(n => n.id !== id));
    }, []);

    return (
        <NotificationsContext.Provider value={{
            notifications,
            unreadCount,
            pushNotification,
            markAllRead,
            markRead,
            clearAll,
            dismiss,
        }}>
            {children}
        </NotificationsContext.Provider>
    );
}

export function useNotifications() {
    const ctx = useContext(NotificationsContext);
    if (!ctx) throw new Error('useNotifications must be inside NotificationsProvider');
    return ctx;
}
