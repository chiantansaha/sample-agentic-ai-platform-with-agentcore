interface BadgeProps {
  children: React.ReactNode;
  variant?: 'success' | 'warning' | 'error' | 'primary' | 'gray';
  className?: string;
}

export function Badge({ children, variant = 'gray', className = '' }: BadgeProps) {
  const variantClasses = {
    success: 'bg-green-100 text-green-700 border border-green-300',
    warning: 'bg-amber-100 text-amber-700 border border-amber-300',
    error: 'bg-red-100 text-red-700 border border-red-300',
    primary: 'bg-blue-100 text-blue-700 border border-blue-300',
    gray: 'bg-gray-100 text-gray-700 border border-gray-300',
  };

  return (
    <span
      className={`inline-flex items-center px-3 py-1 rounded-md text-xs font-medium ${variantClasses[variant]} ${className}`}
    >
      {children}
    </span>
  );
}
