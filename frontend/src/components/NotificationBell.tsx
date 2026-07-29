// frontend/src/components/NotificationBell.tsx
import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { getMyNotifications, markNotificationRead } from '../api/client';
import type { NotificationRow } from '../api/client';

const POLL_INTERVAL_MS = 30_000;

export default function NotificationBell() {
  const [notifications, setNotifications] = useState<NotificationRow[]>([]);
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  const load = useCallback(async () => {
    try {
      const data = await getMyNotifications();
      setNotifications(data);
    } catch {
      // silent - the bell just shows nothing new this cycle
    }
  }, []);

  useEffect(() => {
    load();
    const interval = setInterval(load, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [load]);

  // Close the dropdown on an outside click.
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const handleOpen = () => {
    setOpen((prev) => !prev);
  };

  const handleNotificationClick = async (notification: NotificationRow) => {
    if (!notification.is_read) {
      try {
        await markNotificationRead(notification.id);
        setNotifications((prev) =>
          prev.map((n) => (n.id === notification.id ? { ...n, is_read: true } : n))
        );
      } catch {
        // ignore - not critical if this particular mark-read call fails
      }
    }
    setOpen(false);
    navigate('/slips');
  };

  const timeAgo = (iso: string) => {
    const diffMs = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diffMs / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  };

  return (
    <div className="relative" ref={containerRef}>
      <motion.button
        onClick={handleOpen}
        className="relative material-symbols-outlined text-on-surface-variant cursor-pointer"
        whileHover={{ scale: 1.2, rotate: 10, color: '#00478d' }}
        transition={{ type: 'spring', stiffness: 300 }}
        title="Notifications"
      >
        notifications
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 bg-tertiary text-on-tertiary text-[10px] font-bold rounded-full h-4 min-w-[16px] px-1 flex items-center justify-center">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </motion.button>

      <AnimatePresence>
        {open && (
          <motion.div
            className="absolute right-0 mt-3 w-80 bg-white rounded-xl border border-outline-variant shadow-lg overflow-hidden z-50"
            initial={{ opacity: 0, y: -8, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.97 }}
            transition={{ duration: 0.15 }}
          >
            <div className="px-4 py-3 border-b border-outline-variant bg-surface-container-high">
              <h3 className="text-sm font-semibold text-primary">Notifications</h3>
            </div>
            <div className="max-h-80 overflow-y-auto">
              {notifications.length === 0 ? (
                <p className="text-sm text-on-surface-variant text-center py-6">No notifications yet.</p>
              ) : (
                notifications.map((n) => (
                  <button
                    key={n.id}
                    onClick={() => handleNotificationClick(n)}
                    className={`w-full text-left px-4 py-3 border-b border-outline-variant/50 last:border-0 hover:bg-surface-container-low transition-colors flex gap-2 ${
                      !n.is_read ? 'bg-primary-container/20' : ''
                    }`}
                  >
                    {!n.is_read && <span className="h-2 w-2 rounded-full bg-primary mt-1.5 shrink-0" />}
                    <div className={!n.is_read ? '' : 'ml-4'}>
                      <p className="text-sm text-on-surface">{n.message}</p>
                      <p className="text-xs text-on-surface-variant mt-0.5">{timeAgo(n.created_at)}</p>
                    </div>
                  </button>
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}