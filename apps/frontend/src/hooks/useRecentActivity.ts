import { useEffect } from 'react';

export interface RecentActivityItem {
  id: string;
  type: 'mcp' | 'agent' | 'kb';
  name: string;
  timestamp: string;
}

const STORAGE_KEY = 'recentActivities';
const MAX_ACTIVITIES = 5;

export const useRecentActivity = () => {
  const addActivity = (item: Omit<RecentActivityItem, 'timestamp'>) => {
    const activities = getRecentActivities();

    // Remove if already exists
    const filtered = activities.filter(a => !(a.id === item.id && a.type === item.type));

    // Add new item at the beginning
    const newActivities = [
      {
        ...item,
        timestamp: new Date().toISOString(),
      },
      ...filtered,
    ].slice(0, MAX_ACTIVITIES);

    localStorage.setItem(STORAGE_KEY, JSON.stringify(newActivities));
  };

  const getRecentActivities = (): RecentActivityItem[] => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch (error) {
      console.error('Failed to parse recent activities:', error);
      return [];
    }
  };

  const clearRecentActivities = () => {
    localStorage.removeItem(STORAGE_KEY);
  };

  return {
    addActivity,
    getRecentActivities,
    clearRecentActivities,
  };
};

// Hook for detail pages to automatically track visits
export const useTrackPageVisit = (type: 'mcp' | 'agent' | 'kb', id: string | undefined, name: string | undefined) => {
  const { addActivity } = useRecentActivity();

  useEffect(() => {
    if (id && name) {
      addActivity({ id, type, name });
    }
  }, [id, name, type]);
};
