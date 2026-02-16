import React from 'react';

interface NotificationProps {
  message: string;
  type: 'success' | 'error';
  onClose: () => void;
}

const Notification: React.FC<NotificationProps> = ({ message, type, onClose }) => {
  return (
    <div
      className={`fixed bottom-6 right-6 z-50 px-4 py-2 rounded shadow-lg text-white font-semibold flex items-center gap-2 transition-all animate-fade-in-up
        text-sm min-w-[220px] max-w-xs
        ${type === 'success' ? 'bg-emerald-600' : 'bg-red-600'}`}
      role="alert"
    >
      <span className="text-base">{type === 'success' ? '✔️' : '❌'}</span>
      <span className="truncate flex-1">{message}</span>
      <button onClick={onClose} className="ml-2 text-white/80 hover:text-white font-bold text-base">×</button>
    </div>
  );
};

export default Notification;
