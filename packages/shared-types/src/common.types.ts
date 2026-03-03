/**
 * Common shared types
 */

export type Status = 'active' | 'inactive' | 'pending' | 'failed';

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  hasNext: boolean;
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}
