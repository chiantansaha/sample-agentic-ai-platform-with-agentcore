/**
 * Axios instance for API requests
 */
import axios, { AxiosError } from 'axios';

// Create axios instance
const api = axios.create({
  baseURL: '/api/v1',
  timeout: 600000, // 10 minutes (Internal Deploy MCP takes time for Runtime/Gateway creation)
  headers: {
    'Content-Type': 'application/json',
  },
  paramsSerializer: {
    serialize: (params) => {
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        if (Array.isArray(value)) {
          // For arrays, repeat the parameter: teamTags=id1&teamTags=id2
          value.forEach((item) => searchParams.append(key, item));
        } else if (value !== undefined && value !== null) {
          searchParams.append(key, String(value));
        }
      });
      return searchParams.toString();
    },
  },
});

// Response interceptor: Handle common errors
api.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error: AxiosError) => {
    // Handle 403 Forbidden
    if (error.response?.status === 403) {
      console.error('Forbidden - insufficient permissions');
    }

    // Handle 500 Server Error
    if (error.response?.status === 500) {
      console.error('Server error:', error.response.data);
    }

    return Promise.reject(error);
  }
);

export default api;

// Export convenience methods
export const apiClient = {
  get: api.get,
  post: api.post,
  put: api.put,
  patch: api.patch,
  delete: api.delete,
};
