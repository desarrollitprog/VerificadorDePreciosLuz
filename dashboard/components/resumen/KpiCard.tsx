import React, { useEffect, useRef, useState } from 'react';
import { LucideIcon } from 'lucide-react';

interface KpiCardProps {
  icon: LucideIcon;
  label: string;
  value: number;
  subtitle: string;
  color: 'cyan' | 'emerald' | 'violet' | 'amber';
  loading?: boolean;
}

const colorMap: Record<string, { text: string; bg: string; glow: string; border: string }> = {
  cyan: { text: 'text-cyan-400', bg: 'bg-cyan-500/10', glow: 'shadow-cyan-500/20', border: 'border-cyan-500/20' },
  emerald: { text: 'text-emerald-400', bg: 'bg-emerald-500/10', glow: 'shadow-emerald-500/20', border: 'border-emerald-500/20' },
  violet: { text: 'text-violet-400', bg: 'bg-violet-500/10', glow: 'shadow-violet-500/20', border: 'border-violet-500/20' },
  amber: { text: 'text-amber-400', bg: 'bg-amber-500/10', glow: 'shadow-amber-500/20', border: 'border-amber-500/20' },
};

function useCounter(end: number, duration: number): number {
  const [count, setCount] = useState(0);
  const startRef = useRef<number | null>(null);
  const rafRef = useRef<number>(0);

  useEffect(() => {
    startRef.current = null;
    const step = (timestamp: number) => {
      if (startRef.current === null) startRef.current = timestamp;
      const elapsed = timestamp - startRef.current;
      const progress = Math.min(elapsed / duration, 1);
      setCount(Math.floor(progress * end));
      if (progress < 1) rafRef.current = requestAnimationFrame(step);
    };
    rafRef.current = requestAnimationFrame(step);
    return () => cancelAnimationFrame(rafRef.current);
  }, [end, duration]);

  return count;
}

const KpiCard: React.FC<KpiCardProps> = ({ icon: Icon, label, value, subtitle, color, loading }) => {
  const c = colorMap[color];
  const animated = useCounter(value, 800);

  if (loading) {
    return (
      <div className="bg-[#18181b] rounded-xl border border-zinc-800 p-5 animate-pulse">
        <div className="flex items-start gap-4">
          <div className="h-12 w-12 rounded-lg bg-zinc-800" />
          <div className="flex-1 space-y-3">
            <div className="h-8 w-24 bg-zinc-800 rounded" />
            <div className="h-4 w-20 bg-zinc-800 rounded" />
            <div className="h-3 w-32 bg-zinc-800 rounded" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-[#18181b] rounded-xl border ${c.border} ${c.glow} p-5 hover:shadow-lg hover:shadow-${color}-500/10 transition-all duration-300`}>
      <div className="flex items-start gap-4">
        <div className={`h-12 w-12 rounded-lg ${c.bg} flex items-center justify-center shrink-0`}>
          <Icon size={24} className={c.text} />
        </div>
        <div className="flex-1 min-w-0">
          <span className={`text-3xl font-bold font-sans tracking-tight ${c.text}`}>
            {animated.toLocaleString()}
          </span>
          <p className="text-zinc-400 text-sm font-medium mt-0.5">{label}</p>
          <p className="text-zinc-500 text-xs mt-1 truncate">{subtitle}</p>
        </div>
      </div>
    </div>
  );
};

export default KpiCard;
