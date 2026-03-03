import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Settings } from '../types';

interface SettingsStore {
  settings: Settings;
  updateSettings: (settings: Partial<Settings>) => void;
  updateGeneralSettings: (settings: Partial<Settings['general']>) => void;
  updateSecuritySettings: (settings: Partial<Settings['security']>) => void;
  updateNotificationSettings: (settings: Partial<Settings['notifications']>) => void;
  resetSettings: () => void;
}

const defaultSettings: Settings = {
  general: {
    organizationName: 'AWS',
    defaultRegion: 'ap-northeast-2',
    timezone: 'Asia/Seoul',
  },
  security: {
    mfaEnabled: false,
    sessionTimeout: 30,
    allowedIPs: [],
  },
  notifications: {
    email: true,
    slack: false,
    webhookUrl: undefined,
  },
};

export const useSettingsStore = create<SettingsStore>()(
  persist(
    (set) => ({
      settings: defaultSettings,

      updateSettings: (newSettings) => {
        set((state) => ({
          settings: {
            ...state.settings,
            ...newSettings,
          },
        }));
      },

      updateGeneralSettings: (newGeneralSettings) => {
        set((state) => ({
          settings: {
            ...state.settings,
            general: {
              ...state.settings.general,
              ...newGeneralSettings,
            },
          },
        }));
      },

      updateSecuritySettings: (newSecuritySettings) => {
        set((state) => ({
          settings: {
            ...state.settings,
            security: {
              ...state.settings.security,
              ...newSecuritySettings,
            },
          },
        }));
      },

      updateNotificationSettings: (newNotificationSettings) => {
        set((state) => ({
          settings: {
            ...state.settings,
            notifications: {
              ...state.settings.notifications,
              ...newNotificationSettings,
            },
          },
        }));
      },

      resetSettings: () => {
        set({ settings: defaultSettings });
      },
    }),
    {
      name: 'settings-storage',
    }
  )
);
