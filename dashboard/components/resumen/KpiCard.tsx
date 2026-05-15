import React, { useEffect, useRef, useState } from 'react';
import { LucideIcon } from 'lucide-react';

interface KpiCardProps {
  icon: LucideIcon;
  label: string;
  value: number;
  subtitle: React.ReactNode;
  color: 'cyan' | 'emerald' | 'violet' | 'amber';
  loading?: boolean;
}

interface CardColors {
  text: string;
  bg: string;
  accent: string;
  iconGlow: string;
  gradient: string;
}

const colorMap: Record<string, CardColors> = {
  cyan: {
    text: 'text-cyan-500 dark:text-cyan-400',
    bg: 'bg-cyan-50 dark:bg-cyan-500/10',
    accent: 'bg-cyan-500',
    iconGlow: 'shadow-cyan-500/20',
    gradient: 'from-white via-white to-cyan-50/50 dark:from-[#1c2936] dark:via-[#1c2936] dark:to-cyan-500/5',
  },
  emerald: {
    text: 'text-emerald-600 dark:text-emerald-400',
    bg: 'bg-emerald-50 dark:bg-emerald-500/10',
    accent: 'bg-emerald-500',
    iconGlow: 'shadow-emerald-500/20',
    gradient: 'from-white via-white to-emerald-50/50 dark:from-[#1c2936] dark:via-[#1c2936] dark:to-emerald-500/5',
  },
  violet: {
    text: 'text-violet-600 dark:text-violet-400',
    bg: 'bg-violet-50 dark:bg-violet-500/10',
    accent: 'bg-violet-500',
    iconGlow: 'shadow-violet-500/20',
    gradient: 'from-white via-white to-violet-50/50 dark:from-[#1c2936] dark:via-[#1c2936] dark:to-violet-500/5',
  },
  amber: {
    text: 'text-amber-600 dark:text-amber-400',
    bg: 'bg-amber-50 dark:bg-amber-500/10',
    accent: 'bg-amber-500',
    iconGlow: 'shadow-amber-500/20',
    gradient: 'from-white via-white to-amber-50/50 dark:from-[#1c2936] dark:via-[#1c2936] dark:to-amber-500/5',
  },
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
      <div className="bg-white dark:bg-[#1c2936] rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden relative">
        <div className="h-1 bg-slate-200 dark:bg-[#253247]" />
        <div className="p-5 animate-pulse">
          <div className="flex items-start gap-4">
            <div className="h-12 w-12 rounded-full bg-slate-200 dark:bg-[#253247] shrink-0" />
            <div className="flex-1 space-y-3">
              <div className="h-8 w-24 bg-slate-200 dark:bg-[#253247] rounded" />
              <div className="h-4 w-20 bg-slate-200 dark:bg-[#253247] rounded" />
              <div className="h-3 w-32 bg-slate-200 dark:bg-[#253247] rounded" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-[#1c2936] rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm hover:shadow-lg transition-all duration-300 hover:-translate-y-0.5 overflow-hidden relative group">
      <div className={`h-1 w-full ${c.accent}`} />
      <div className={`absolute inset-0 bg-gradient-to-br ${c.gradient} pointer-events-none`} />
      <div className="relative z-10 p-5">
        <div className="flex items-start gap-4">
          <div className={`h-12 w-12 rounded-full ${c.bg} ${c.iconGlow} flex items-center justify-center shrink-0 shadow-sm group-hover:shadow-md transition-shadow`}>
            <Icon size={24} className={c.text} />
          </div>
          <div className="flex-1 min-w-0">
            <span className={`text-4xl font-extrabold font-sans tracking-tight ${c.text}`}>
              {animated.toLocaleString()}
            </span>
            <p className="text-slate-600 dark:text-slate-300 text-sm font-medium mt-0.5">{label}</p>
            <div className="text-slate-500 dark:text-slate-400 text-xs mt-1 flex items-center gap-1 flex-wrap">{subtitle}</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default KpiCard;
