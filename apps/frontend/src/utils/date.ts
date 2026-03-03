/**
 * Date/Time Formatting Utilities
 *
 * Backend stores timestamps as Unix timestamp (seconds since epoch, UTC).
 * Frontend converts to browser's local timezone for display.
 *
 * All functions support backward compatibility with ISO string format.
 */

/**
 * Parse timestamp value to Date object
 * Supports both Unix timestamp (seconds) and ISO string format
 */
function parseToDate(value: number | string): Date {
  if (typeof value === 'number') {
    // Unix timestamp (seconds) -> milliseconds
    return new Date(value * 1000);
  }
  // ISO string
  return new Date(value);
}

/**
 * Format timestamp to local time
 */
export function formatLocalTime(value: number | string): string {
  const date = parseToDate(value);
  return date.toLocaleTimeString('ko-KR', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
}

/**
 * Format timestamp to local date and time
 */
export function formatLocalDateTime(value: number | string): string {
  const date = parseToDate(value);
  return date.toLocaleString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
}

/**
 * Format timestamp to local date
 */
export function formatLocalDate(value: number | string): string {
  const date = parseToDate(value);
  return date.toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
}

/**
 * Get timestamp value as number for comparison/sorting
 * Supports both Unix timestamp (seconds) and ISO string format
 */
export function getTimestampValue(value: number | string | undefined | null): number {
  if (value === undefined || value === null) {
    return 0;
  }
  if (typeof value === 'number') {
    return value;
  }
  // ISO string -> Unix timestamp (seconds)
  return Math.floor(new Date(value).getTime() / 1000);
}

/**
 * Format timestamp to relative time (e.g., "2 minutes ago")
 */
export function formatRelativeTime(value: number | string): string {
  const date = parseToDate(value);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffSec < 60) {
    return '방금 전';
  } else if (diffMin < 60) {
    return `${diffMin}분 전`;
  } else if (diffHour < 24) {
    return `${diffHour}시간 전`;
  } else if (diffDay < 7) {
    return `${diffDay}일 전`;
  } else {
    return formatLocalDate(value);
  }
}
