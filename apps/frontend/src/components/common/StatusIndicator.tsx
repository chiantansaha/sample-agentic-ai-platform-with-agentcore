import type { Status, Health } from '../../types';

interface StatusIndicatorProps {
  status?: Status;
  health?: Health;
  label?: string;
  className?: string;
}

export function StatusIndicator({
  status,
  health,
  label,
  className = '',
}: StatusIndicatorProps) {
  // Determine color and label based on status or health
  let bgColor = 'bg-gray-100';
  let textColor = 'text-gray-700';
  let displayLabel = label;

  if (status) {
    if (status === 'enabled') {
      bgColor = 'bg-green-100';
      textColor = 'text-green-700';
      displayLabel = displayLabel || 'Enabled';
    } else {
      bgColor = 'bg-gray-100';
      textColor = 'text-gray-600';
      displayLabel = displayLabel || 'Disabled';
    }
  } else if (health) {
    if (health === 'healthy') {
      bgColor = 'bg-green-100';
      textColor = 'text-green-700';
      displayLabel = displayLabel || 'Healthy';
    } else if (health === 'unhealthy') {
      bgColor = 'bg-red-100';
      textColor = 'text-red-700';
      displayLabel = displayLabel || 'Unhealthy';
    } else {
      bgColor = 'bg-gray-100';
      textColor = 'text-gray-600';
      displayLabel = displayLabel || 'Unknown';
    }
  }

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${bgColor} ${textColor} ${className}`}>
      {displayLabel}
    </span>
  );
}
