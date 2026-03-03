interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  variant?: 'primary' | 'dark' | 'light';
  className?: string;
}

export function LoadingSpinner({ size = 'md', variant = 'primary', className = '' }: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: 'w-4 h-4 border-2',
    md: 'w-8 h-8 border-3',
    lg: 'w-12 h-12 border-4',
  };

  const variantClasses = {
    primary: 'border-blue-600 border-t-transparent',
    dark: 'border-gray-700 border-t-transparent',
    light: 'border-white border-t-transparent',
  };

  return (
    <div
      className={`${sizeClasses[size]} ${variantClasses[variant]} rounded-full animate-spin ${className}`}
      role="status"
      aria-label="Loading"
    />
  );
}
