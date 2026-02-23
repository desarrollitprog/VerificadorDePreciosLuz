import { useState } from 'react';
import axios from 'axios';

export function VideoLibrary() {
  const [syncLoading, setSyncLoading] = useState(false);
  const [syncResult, setSyncResult] = useState<string | null>(null);

  const handleForceSync = async () => {
    setSyncLoading(true);
    setSyncResult(null);
    try {
      // Cambia la URL por la de tu backend-dashboard
      const response = await axios.post('http://192.168.1.105:3000/monitoreo/sincronizar-fuerza');
      if (response.data.success) {
        setSyncResult('Sincronización forzada ejecutada correctamente.');
      } else {
        setSyncResult('Sincronización fallida.');
      }
    } catch (error) {
      setSyncResult('Error al ejecutar la sincronización.');
    } finally {
      setSyncLoading(false);
    }
  };

  return (
    <div className="flex flex-col">
      {/* Barra superior: botón de sincronización forzada */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex-1" />
        <button
          className="bg-blue-600 text-white px-4 py-2 rounded-lg shadow hover:bg-blue-700 transition disabled:opacity-50"
          onClick={handleForceSync}
          disabled={syncLoading}
        >
          {syncLoading ? 'Sincronizando...' : 'Sincronización Forzada'}
        </button>
      </div>
      {syncResult && (
        <div className="mb-4 text-green-600 font-semibold">{syncResult}</div>
      )}
      {/* ...resto del contenido de VideoLibrary... */}
      {/* ...existing code... */}
    </div>
  );
}