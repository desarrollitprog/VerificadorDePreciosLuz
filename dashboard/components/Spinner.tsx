import React from 'react';

interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const sizeMap = {
  sm: 'w-4 h-4 border-2',
  md: 'w-6 h-6 border-2',
  lg: 'w-10 h-10 border-[3px]',
};

export const Spinner: React.FC<SpinnerProps> = ({ size = 'md', className = '' }) => {
  return (
    <div
      className={`${sizeMap[size]} rounded-full border-primary border-t-transparent animate-spin ${className}`}
      role="status"
      aria-label="Cargando"
    />
  );
};
