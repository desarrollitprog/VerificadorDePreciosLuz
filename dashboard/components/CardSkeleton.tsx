import React from 'react';
import { Skeleton } from './Skeleton';

export const CardSkeleton: React.FC = () => {
  return (
    <div className="border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden bg-white dark:bg-slate-800 flex flex-col">
      <div className="relative aspect-video bg-slate-100 dark:bg-slate-700">
        <Skeleton className="absolute inset-0 rounded-none" />
      </div>
      <div className="p-4 flex-1 flex flex-col gap-3">
        <div className="flex justify-between items-start gap-2">
          <Skeleton className="h-5 w-3/5" />
          <Skeleton className="h-5 w-5 shrink-0" />
        </div>
        <div className="flex items-center gap-2">
          <Skeleton className="h-5 w-16 rounded-full" />
          <Skeleton className="h-5 w-14 rounded-full" />
        </div>
        <Skeleton className="h-4 w-4/5" />
        <Skeleton className="h-4 w-2/5" />
        <div className="flex items-center gap-2 mt-auto pt-3 border-t border-slate-100 dark:border-slate-700/50">
          <Skeleton className="h-8 flex-1 rounded-lg" />
          <Skeleton className="h-8 flex-1 rounded-lg" />
          <Skeleton className="h-8 flex-1 rounded-lg" />
        </div>
      </div>
    </div>
  );
};
