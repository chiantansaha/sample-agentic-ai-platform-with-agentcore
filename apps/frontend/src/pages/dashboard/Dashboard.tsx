import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Card, LoadingSpinner } from '../../components/common';
import { useRecentActivity, RecentActivityItem } from '../../hooks/useRecentActivity';
import { formatLocalDateTime } from '../../utils/date';
import api from '../../utils/axios';

interface DashboardStats {
  mcps: {
    total: number;
    enabled: number;
    healthy: number;
  };
  agents: {
    total: number;
    enabled: number;
    production: number;
  };
  knowledgeBases: {
    total: number;
    enabled: number;
    totalDocuments: number;
  };
}

export function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentActivities, setRecentActivities] = useState<RecentActivityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const { getRecentActivities } = useRecentActivity();

  useEffect(() => {
    // Fetch dashboard stats
    const fetchStats = async () => {
      try {
        const response = await api.get('/dashboard/stats');
        setStats(response.data.data);
      } catch (error) {
        console.error('Failed to fetch stats:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();

    // Load recent activities from localStorage
    setRecentActivities(getRecentActivities());
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Failed to load dashboard stats</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600 mt-2">
          AWS Agentic AI Platform 대시보드
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* MCPs Card */}
        <Link to="/mcps" className="group">
          <div className="relative overflow-hidden bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1">
            <div className="relative p-6 text-white">
              <div className="flex items-center justify-between mb-4">
                <svg className="w-10 h-10" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                <div className="text-right">
                  <p className="text-sm font-medium text-blue-100">MCPs</p>
                  <p className="text-4xl font-bold">{stats.mcps.total}</p>
                </div>
              </div>
              <div className="flex justify-between text-sm border-t border-white border-opacity-20 pt-3">
                <span className="text-blue-100">Enabled: {stats.mcps.enabled}</span>
                <span className="text-blue-100">Healthy: {stats.mcps.healthy}</span>
              </div>
            </div>
          </div>
        </Link>

        {/* Agents Card */}
        <Link to="/agents" className="group">
          <div className="relative overflow-hidden bg-gradient-to-br from-green-500 to-green-600 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1">
            <div className="relative p-6 text-white">
              <div className="flex items-center justify-between mb-4">
                <svg className="w-10 h-10" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
                </svg>
                <div className="text-right">
                  <p className="text-sm font-medium text-green-100">Agents</p>
                  <p className="text-4xl font-bold">{stats.agents.total}</p>
                </div>
              </div>
              <div className="text-sm border-t border-white border-opacity-20 pt-3">
                <span className="text-green-100">Enabled: {stats.agents.enabled}</span>
              </div>
            </div>
          </div>
        </Link>

        {/* Knowledge Bases Card */}
        <Link to="/knowledge-bases" className="group">
          <div className="relative overflow-hidden bg-gradient-to-br from-amber-500 to-amber-600 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1">
            <div className="relative p-6 text-white">
              <div className="flex items-center justify-between mb-4">
                <svg className="w-10 h-10" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                </svg>
                <div className="text-right">
                  <p className="text-sm font-medium text-amber-100">Knowledge Bases</p>
                  <p className="text-4xl font-bold">{stats.knowledgeBases.total}</p>
                </div>
              </div>
              <div className="text-sm border-t border-white border-opacity-20 pt-3">
                <span className="text-amber-100">Enabled: {stats.knowledgeBases.enabled}</span>
              </div>
            </div>
          </div>
        </Link>
      </div>

      {/* Quick Actions */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Link
            to="/mcps/create"
            className="group p-5 bg-white rounded-xl shadow-sm border-2 border-gray-200 hover:border-blue-500 hover:shadow-lg transition-all duration-300 transform hover:-translate-y-1"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center group-hover:bg-blue-100 transition-colors">
                <svg className="w-6 h-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
              </div>
              <div>
                <div className="font-semibold text-gray-900 group-hover:text-blue-600 transition-colors">Create MCP</div>
                <div className="text-xs text-gray-500 mt-0.5">Add new MCP</div>
              </div>
            </div>
          </Link>

          <Link
            to="/agents/create"
            className="group p-5 bg-white rounded-xl shadow-sm border-2 border-gray-200 hover:border-green-500 hover:shadow-lg transition-all duration-300 transform hover:-translate-y-1"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-green-50 rounded-lg flex items-center justify-center group-hover:bg-green-100 transition-colors">
                <svg className="w-6 h-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
              </div>
              <div>
                <div className="font-semibold text-gray-900 group-hover:text-green-600 transition-colors">Create Agent</div>
                <div className="text-xs text-gray-500 mt-0.5">Build new agent</div>
              </div>
            </div>
          </Link>

          <Link
            to="/knowledge-bases/create"
            className="group p-5 bg-white rounded-xl shadow-sm border-2 border-gray-200 hover:border-amber-500 hover:shadow-lg transition-all duration-300 transform hover:-translate-y-1"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-amber-50 rounded-lg flex items-center justify-center group-hover:bg-amber-100 transition-colors">
                <svg className="w-6 h-6 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
              </div>
              <div>
                <div className="font-semibold text-gray-900 group-hover:text-amber-600 transition-colors">Create KB</div>
                <div className="text-xs text-gray-500 mt-0.5">Add knowledge base</div>
              </div>
            </div>
          </Link>

          <Link
            to="/playground"
            className="group p-5 bg-white rounded-xl shadow-sm border-2 border-gray-200 hover:border-purple-500 hover:shadow-lg transition-all duration-300 transform hover:-translate-y-1"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-purple-50 rounded-lg flex items-center justify-center group-hover:bg-purple-100 transition-colors">
                <svg className="w-6 h-6 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div>
                <div className="font-semibold text-gray-900 group-hover:text-purple-600 transition-colors">Playground</div>
                <div className="text-xs text-gray-500 mt-0.5">Test agents</div>
              </div>
            </div>
          </Link>
        </div>
      </div>

      {/* Recent Activity Section */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Recent Activity</h2>
        <Card>
          {recentActivities.length === 0 ? (
            <p className="text-sm text-gray-500 text-center py-8">
              최근 활동이 없습니다.
            </p>
          ) : (
            <div className="space-y-3">
              {recentActivities.map((activity) => {
                const typeConfig = {
                  mcp: { color: 'text-blue-600', bg: 'bg-blue-50', label: 'MCP', link: `/mcps/${activity.id}` },
                  agent: { color: 'text-green-600', bg: 'bg-green-50', label: 'Agent', link: `/agents/${activity.id}` },
                  kb: { color: 'text-amber-600', bg: 'bg-amber-50', label: 'KB', link: `/knowledge-bases/${activity.id}` },
                };
                const config = typeConfig[activity.type];

                return (
                  <Link
                    key={`${activity.type}-${activity.id}`}
                    to={config.link}
                    className="flex items-center gap-4 p-3 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    <div className={`w-10 h-10 rounded-lg ${config.bg} flex items-center justify-center flex-shrink-0`}>
                      <span className={`text-sm font-semibold ${config.color}`}>
                        {config.label}
                      </span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {activity.name}
                      </p>
                      <p className="text-xs text-gray-500">
                        최근 방문 • {formatLocalDateTime(activity.timestamp)}
                      </p>
                    </div>
                  </Link>
                );
              })}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
