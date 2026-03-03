import { ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
  hoverable?: boolean;
  onClick?: () => void;
}

export function Card({ children, className = '', hoverable = false, onClick }: CardProps) {
  const hoverClass = hoverable ? 'card-hover cursor-pointer' : '';
  const clickable = onClick ? 'cursor-pointer' : '';

  return (
    <div
      className={`bg-white rounded-lg shadow-sm p-6 ${hoverClass} ${clickable} ${className}`}
      onClick={onClick}
    >
      {children}
    </div>
  );
}
