import React, { useState } from 'react';
import { useNotification } from './useNotification';

const NotificationExample: React.FC = () => {
  const showNotification = useNotification();
  const [input, setInput] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input) {
      showNotification('Por favor ingresa un texto', 'error');
      return;
    }
    showNotification(`Mensaje enviado: ${input}`, 'success');
    setInput('');
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-2 items-center">
      <input
        className="border rounded px-2 py-1"
        value={input}
        onChange={e => setInput(e.target.value)}
        placeholder="Escribe algo..."
      />
      <button className="bg-blue-600 text-white px-3 py-1 rounded" type="submit">Enviar</button>
    </form>
  );
};

export default NotificationExample;
