import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';

interface NavItem {
  path: string;
  label: string;
  icon: React.ReactNode;
  badge?: string;
  disabled?: boolean;
}

interface NavGroup {
  label: string;
  icon: React.ReactNode;
  items: NavItem[];
  defaultOpen?: boolean;
}

const navStructure = {
  topLevel: [
    {
      path: '/',
      label: 'Dashboard',
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
        </svg>
      )
    },
  ],
  groups: [
    {
      label: 'Resources',
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
        </svg>
      ),
      defaultOpen: true,
      items: [
        {
          path: '/mcps',
          label: 'MCP Registry',
          icon: (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          )
        },
        {
          path: '/knowledge-bases',
          label: 'Knowledge Bases',
          icon: (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
          )
        },
      ],
    },
    {
      label: 'Agent',
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
      ),
      defaultOpen: true,
      items: [
        {
          path: '/agents',
          label: 'Agents',
          icon: (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          )
        },
        {
          path: '/playground',
          label: 'Playground',
          icon: (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          )
        },
      ],
    },
  ] as NavGroup[],
  bottomLevel: [
    {
      path: '/settings',
      label: 'Settings',
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      )
    },
  ],
};

export function Sidebar() {
  const location = useLocation();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>(
    navStructure.groups.reduce((acc, group) => {
      acc[group.label] = group.defaultOpen ?? false;
      return acc;
    }, {} as Record<string, boolean>)
  );

  const toggleGroup = (groupLabel: string) => {
    if (isCollapsed) return;
    setOpenGroups((prev) => ({
      ...prev,
      [groupLabel]: !prev[groupLabel],
    }));
  };

  const toggleSidebar = () => {
    setIsCollapsed((prev) => !prev);
  };

  const isItemActive = (path: string) => {
    if (path === '/') {
      return location.pathname === path;
    }
    return location.pathname.startsWith(path);
  };

  return (
    <aside
      className={`relative bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 h-full overflow-y-auto transition-all duration-300 ${isCollapsed ? 'w-20' : 'w-64'}`}
    >
      {/* Toggle Button */}
      <button
        onClick={toggleSidebar}
        className="absolute z-10 top-1/2 -translate-y-1/2 -right-3 p-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-sm text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-all duration-200"
        title={isCollapsed ? '사이드바 펼치기' : '사이드바 접기'}
      >
        {isCollapsed ? (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
          </svg>
        ) : (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
          </svg>
        )}
      </button>

      <nav className="p-4 space-y-1">
        {/* Top Level Items */}
        {navStructure.topLevel.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            className={`
              flex items-center gap-3 px-3 py-3 rounded-lg text-sm font-medium transition-colors
              ${
                isItemActive(item.path)
                  ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-gray-100'
              }
              ${isCollapsed ? 'justify-center' : ''}
            `}
            title={isCollapsed ? item.label : undefined}
          >
            {isCollapsed && <span className="text-xl">{item.icon}</span>}
            {!isCollapsed && <span>{item.label}</span>}
          </Link>
        ))}

        {/* Divider */}
        <div className="border-t border-gray-200 dark:border-gray-700 my-2" />

        {/* Grouped Items */}
        {navStructure.groups.map((group) => {
          const isOpen = openGroups[group.label] && !isCollapsed;

          return (
            <div key={group.label} className="space-y-1">
              {/* Group Header */}
              {isCollapsed ? (
                <div
                  className="flex items-center justify-center px-3 py-2 text-gray-500 dark:text-gray-400"
                  title={group.label}
                >
                  {group.icon}
                </div>
              ) : (
                <button
                  onClick={() => toggleGroup(group.label)}
                  className="w-full flex items-center justify-between px-3 py-2 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
                >
                  <span>{group.label}</span>
                  <span className="text-sm">
                    {isOpen ? '▼' : '▶'}
                  </span>
                </button>
              )}

              {/* Group Items */}
              {isOpen && (
                <div className="space-y-1">
                  {group.items.map((item) =>
                    item.disabled ? (
                      <div
                        key={item.path}
                        className="flex items-center gap-2 px-3 py-2 pl-8 rounded-lg text-sm font-medium text-gray-400 dark:text-gray-500 cursor-not-allowed whitespace-nowrap"
                      >
                        <span>{item.label}</span>
                        {item.badge && (
                          <span className="shrink-0 px-2 py-0.5 text-xs font-medium bg-amber-100 text-amber-700 rounded-full">
                            {item.badge}
                          </span>
                        )}
                      </div>
                    ) : (
                      <Link
                        key={item.path}
                        to={item.path}
                        className={`
                          flex items-center gap-3 px-3 py-2 pl-8 rounded-lg text-sm font-medium transition-colors
                          ${
                            isItemActive(item.path)
                              ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
                              : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-gray-100'
                          }
                        `}
                      >
                        <span>{item.label}</span>
                        {item.badge && (
                          <span className="ml-auto px-2 py-0.5 text-xs bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-400 rounded-full">
                            {item.badge}
                          </span>
                        )}
                      </Link>
                    )
                  )}
                </div>
              )}

              {/* Collapsed: Show items as icons only */}
              {isCollapsed && (
                <div className="space-y-1">
                  {group.items.map((item) =>
                    item.disabled ? (
                      <div
                        key={item.path}
                        className="flex items-center justify-center px-3 py-2 rounded-lg text-sm font-medium text-gray-400 dark:text-gray-500 cursor-not-allowed"
                        title={`${item.label}${item.badge ? ` (${item.badge})` : ''}`}
                      >
                        <span className="text-xl">{item.icon}</span>
                      </div>
                    ) : (
                      <Link
                        key={item.path}
                        to={item.path}
                        className={`
                          flex items-center justify-center px-3 py-2 rounded-lg text-sm font-medium transition-colors
                          ${
                            isItemActive(item.path)
                              ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
                              : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-gray-100'
                          }
                        `}
                        title={item.label}
                      >
                        <span className="text-xl">{item.icon}</span>
                      </Link>
                    )
                  )}
                </div>
              )}
            </div>
          );
        })}

        {/* Divider */}
        <div className="border-t border-gray-200 dark:border-gray-700 my-2" />

        {/* Bottom Level Items */}
        {navStructure.bottomLevel.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            className={`
              flex items-center gap-3 px-3 py-3 rounded-lg text-sm font-medium transition-colors
              ${
                isItemActive(item.path)
                  ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-gray-100'
              }
              ${isCollapsed ? 'justify-center' : ''}
            `}
            title={isCollapsed ? item.label : undefined}
          >
            {isCollapsed && <span className="text-xl">{item.icon}</span>}
            {!isCollapsed && <span>{item.label}</span>}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
