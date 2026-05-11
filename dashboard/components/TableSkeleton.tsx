import React from 'react';
import { Skeleton } from './Skeleton';

interface TableSkeletonProps {
  rows?: number;
  cols?: number;
  className?: string;
}

export const TableSkeleton: React.FC<TableSkeletonProps> = ({ rows = 5, cols = 5, className = '' }) => {
  return (
    <tbody className={className}>
      {Array.from({ length: rows }).map((_, rowIdx) => (
        <tr key={rowIdx}>
          {Array.from({ length: cols }).map((_, colIdx) => (
            <td key={colIdx} className="px-4 py-3">
              <Skeleton className="h-5 w-full" />
            </td>
          ))}
        </tr>
      ))}
    </tbody>
  );
};
