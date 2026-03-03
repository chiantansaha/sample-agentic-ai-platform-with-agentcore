import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import type { Gateway } from '../../types';
import { Card, LoadingSpinner, StatusIndicator, Badge } from '../../components/common';

export function GatewayList() {
  const [gateways, setGateways] = useState<Gateway[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/gateways')
      .then(res => res.json())
      .then(data => { setGateways(data.data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex items-center justify-center h-64"><LoadingSpinner size="lg" /></div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Gateways</h1>
          <p className="text-gray-600 mt-1">Manage your API gateways</p>
        </div>
        <Link
          to="/gateways/create"
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium shadow-sm"
        >
          + Create Gateway
        </Link>
      </div>
      <div className="grid grid-cols-4 gap-6">
        {gateways.map(gw => (
          <Link key={gw.id} to={`/gateways/${gw.id}`}>
            <Card hoverable>
              <div className="flex items-start justify-between mb-3">
                <h3 className="font-semibold text-gray-900">{gw.name}</h3>
                <Badge variant={gw.type === 'dedicated' ? 'primary' : 'success'}>
                  {gw.type}
                </Badge>
              </div>
              <p className="text-xs text-gray-500 font-mono mb-4">{gw.endpoint}</p>
              <div className="flex items-center gap-2">
                <StatusIndicator status={gw.status} />
                <StatusIndicator health={gw.health} />
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
