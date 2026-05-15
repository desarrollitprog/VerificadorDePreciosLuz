import React, { useEffect, useState, useCallback } from 'react';
import { RefreshCw, Server, Smartphone, Film, Users, AlertCircle } from 'lucide-react';
import { fetchResumen, ResumenData } from '../services/resumenService';
import KpiCard from '../components/resumen/KpiCard';
import ServerStorageChart from '../components/resumen/ServerStorageChart';
import DeviceStatusChart from '../components/resumen/DeviceStatusChart';
import BannersTimeline from '../components/resumen/BannersTimeline';
import ServerMiniTable from '../components/resumen/ServerMiniTable';

export const ResumenScreen: React.FC = () => {
  const [data, setData] = useState<ResumenData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const load = useCallback(async () => {
    try {
      setError(null);
      const result = await fetchResumen();
      setData(result);
      setLastUpdated(new Date());
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Error al cargar resumen');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 60000);
    return () => clearInterval(id);
  }, [load]);

  if (error && !data) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <AlertCircle size={48} className="text-red-400 mb-4" />
          <p className="text-zinc-300 text-lg font-medium mb-2">Error al cargar el resumen</p>
          <p className="text-zinc-500 text-sm mb-6">{error}</p>
          <button
            onClick={load}
            className="flex items-center gap-2 px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg transition-colors text-sm"
          >
            <RefreshCw size={16} />
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Resumen</h1>
        <div className="flex items-center gap-3">
          {lastUpdated && (
            <span className="text-xs text-zinc-500">
              Última actualización: {lastUpdated.toLocaleTimeString('es-VE', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            </span>
          )}
          <button
            onClick={load}
            disabled={loading}
            className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-lg transition-colors disabled:opacity-50"
            title="Actualizar"
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {loading && !data && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <KpiCard icon={Server} label="Servidores" value={0} subtitle="" color="cyan" loading />
          <KpiCard icon={Smartphone} label="Dispositivos" value={0} subtitle="" color="emerald" loading />
          <KpiCard icon={Film} label="Archivos" value={0} subtitle="" color="violet" loading />
          <KpiCard icon={Users} label="Usuarios" value={0} subtitle="" color="amber" loading />
        </div>
      )}

      {data && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 stagger-1">
            <KpiCard
              icon={Server}
              label="Servidores"
              value={data.servidores.total}
              subtitle={`${data.servidores.online} online · ${data.servidores.offline} offline`}
              color="cyan"
            />
            <KpiCard
              icon={Smartphone}
              label="Dispositivos"
              value={data.dispositivos.total}
              subtitle={`${data.dispositivos.online} online · ${data.dispositivos.offline} offline`}
              color="emerald"
            />
            <KpiCard
              icon={Film}
              label="Archivos"
              value={data.banners.total}
              subtitle={`${data.banners.activos} activos · ${data.banners.vencidos} vencidos`}
              color="violet"
            />
            <KpiCard
              icon={Users}
              label="Usuarios"
              value={data.usuarios.total}
              subtitle={`${data.usuarios.activos} activos`}
              color="amber"
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 stagger-2">
            <DeviceStatusChart data={data.dispositivos} />
            <ServerStorageChart data={data.servidores_detalle} />
          </div>

          <div className="stagger-3">
            <BannersTimeline data={data.historial_subidas} />
          </div>

          <div className="stagger-4">
            <ServerMiniTable data={data.servidores_detalle} />
          </div>
        </>
      )}
    </div>
  );
};


