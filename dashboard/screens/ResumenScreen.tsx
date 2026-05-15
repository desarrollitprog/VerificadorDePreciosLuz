import React, { useEffect, useState, useCallback } from 'react';
import { RefreshCw, Server, Smartphone, Film, Users, AlertCircle } from 'lucide-react';
import { fetchResumen, ResumenData } from '../services/resumenService';
import { getUserRole } from '../services/tokenUtils';
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
  const role = getUserRole();

  const load = useCallback(async () => {
    try {
      setLoading(true);
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
          <p className="text-slate-600 dark:text-slate-300 text-lg font-medium mb-2">Error al cargar el resumen</p>
          <p className="text-slate-500 dark:text-slate-400 text-sm mb-6">{error}</p>
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
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Dashboard</h1>
        <div className="flex items-center gap-3">
          {lastUpdated && (
            <span className="text-xs text-slate-500 dark:text-zinc-500">
              Última actualización: {lastUpdated.toLocaleTimeString('es-VE', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            </span>
          )}
          <button
            onClick={load}
            disabled={loading}
            className="p-2 text-slate-500 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200 dark:hover:bg-[#253247] rounded-lg transition-colors disabled:opacity-50"
            title="Actualizar"
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {loading && !data && (
        <div className="grid grid-cols-4 gap-4">
          <KpiCard icon={Server} label="Sedes" value={0} subtitle="" color="cyan" loading />
          <KpiCard icon={Smartphone} label="Dispositivos" value={0} subtitle="" color="emerald" loading />
          <KpiCard icon={Film} label="Archivos" value={0} subtitle="" color="violet" loading />
          {role === 'ADMIN' && <KpiCard icon={Users} label="Usuarios" value={0} subtitle="" color="amber" loading />}
        </div>
      )}

      {data && (
        <>
          <div className="grid grid-cols-4 gap-4 stagger-1">
            <KpiCard
              icon={Server}
              label="Sedes"
              value={data.servidores.total}
              subtitle={
                <span className="inline-flex items-center gap-1">
                  <span className="inline-flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-green-500" />{data.servidores.online} online</span>
                  <span className="mx-1.5 text-slate-400">·</span>
                  <span className="inline-flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-red-500" />{data.servidores.offline} offline</span>
                </span>
              }
              color="cyan"
            />
            <KpiCard
              icon={Smartphone}
              label="Dispositivos"
              value={data.dispositivos.total}
              subtitle={
                <span className="inline-flex items-center gap-1">
                  <span className="inline-flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-green-500" />{data.dispositivos.online} online</span>
                  <span className="mx-1.5 text-slate-400">·</span>
                  <span className="inline-flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-red-500" />{data.dispositivos.offline} offline</span>
                </span>
              }
              color="emerald"
            />
            <KpiCard
              icon={Film}
              label="Archivos"
              value={data.banners.total}
              subtitle={`${data.banners.programados} programados · ${data.banners.vencidos} vencidos`}
              color="violet"
            />
            {role === 'ADMIN' && (
              <KpiCard
                icon={Users}
                label="Usuarios"
                value={data.usuarios.total}
                subtitle={`${data.usuarios.activos} activos`}
                color="amber"
              />
            )}
          </div>

          <div className={`grid grid-cols-1 gap-6 stagger-2 ${role === 'ADMIN' ? 'lg:grid-cols-2' : ''}`}>
            <DeviceStatusChart data={data.dispositivos} />
            {role === 'ADMIN' && <ServerStorageChart data={data.servidores_detalle} />}
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


