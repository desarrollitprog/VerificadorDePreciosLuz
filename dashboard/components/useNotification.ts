import { useNotificationContext } from './NotificationContext';

export const useNotification = () => {
  const { showNotification } = useNotificationContext();
  return showNotification;
};
