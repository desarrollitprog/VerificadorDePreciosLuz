import React, { createContext, useContext, useState, ReactNode, useCallback, useMemo } from 'react';

export type NotificationType = 'success' | 'error' | 'info' | 'warning';
export interface Notification {
  id: string;
  message: string;
  type: NotificationType;
  duration?: number;
  persistent?: boolean;
}

interface NotificationContextProps {
  notifications: Notification[];
  showNotification: (message: string, type: NotificationType, duration?: number) => void;
  removeNotification: (id: string) => void;
  removeAll: () => void;
}

const NotificationContext = createContext<NotificationContextProps | undefined>(undefined);

const MAX_NOTIFICATIONS = 5;

export const NotificationProvider = ({ children }: { children: ReactNode }) => {
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const removeNotification = useCallback((id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, []);

  const removeAll = useCallback(() => {
    setNotifications([]);
  }, []);

  const showNotification = useCallback((message: string, type: NotificationType, duration = 5000) => {
    const id = Math.random().toString(36).substr(2, 9) + Date.now().toString(36);
    const persistent = duration === 0;
    setNotifications((prev) => {
      const next = [...prev, { id, message, type, duration, persistent }];
      return next.length > MAX_NOTIFICATIONS ? next.slice(next.length - MAX_NOTIFICATIONS) : next;
    });
    if (!persistent) {
      setTimeout(() => removeNotification(id), duration);
    }
  }, [removeNotification]);

  const contextValue = useMemo(
    () => ({ notifications, showNotification, removeNotification, removeAll }),
    [notifications, showNotification, removeNotification, removeAll]
  );

  return (
    <NotificationContext.Provider value={contextValue}>
      {children}
    </NotificationContext.Provider>
  );
};

export const useNotificationContext = () => {
  const context = useContext(NotificationContext);
  if (!context) throw new Error('useNotificationContext must be used within NotificationProvider');
  return context;
};
