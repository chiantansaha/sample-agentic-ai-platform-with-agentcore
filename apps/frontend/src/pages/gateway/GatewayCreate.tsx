import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Card, LoadingSpinner } from '../../components/common';

export function GatewayCreate() {
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    type: 'shared' as 'dedicated' | 'shared',
    tags: '',
  });

  const handleSubmit = async () => {
    setError('');

    if (!formData.name) {
      setError('Please provide a gateway name');
      return;
    }

    setSubmitting(true);

    try {
      await new Promise(resolve => setTimeout(resolve, 1500));

      console.log('Creating Gateway:', formData);

      navigate('/gateways');
    } catch (err) {
      setError('Failed to create gateway. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <Link to="/gateways" className="text-sm text-gray-500 hover:text-gray-700 mb-2 inline-block">
          ← Back to Gateways
        </Link>
        <h1 className="text-3xl font-bold text-gray-900">Create Gateway</h1>
        <p className="text-gray-600 mt-1">
          Set up a new shared gateway for multiple MCPs
        </p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Basic Information */}
      <Card>
        <h3 className="font-semibold text-gray-900 mb-6">Basic Information</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Gateway Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent outline-none"
              placeholder="My Shared Gateway"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent outline-none"
              rows={3}
              placeholder="Description of this gateway..."
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Gateway Type
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setFormData({ ...formData, type: 'shared' })}
                className={`p-3 border-2 rounded-lg text-left transition-all ${
                  formData.type === 'shared'
                    ? 'border-blue-600 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="font-medium text-sm">Shared</div>
                <div className="text-xs text-gray-600 mt-1">Multiple MCPs can use this gateway</div>
              </button>
              <button
                type="button"
                onClick={() => setFormData({ ...formData, type: 'dedicated' })}
                className={`p-3 border-2 rounded-lg text-left transition-all ${
                  formData.type === 'dedicated'
                    ? 'border-blue-600 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="font-medium text-sm">Dedicated</div>
                <div className="text-xs text-gray-600 mt-1">One-to-one mapping with MCP</div>
              </button>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Note: Dedicated gateways are typically auto-created when creating Internal MCPs
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Tags (comma-separated)
            </label>
            <input
              type="text"
              value={formData.tags}
              onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent outline-none"
              placeholder="production, external, high-priority"
            />
          </div>
        </div>
      </Card>

      {/* Actions */}
      <div className="flex items-center justify-between pt-6 border-t border-gray-200">
        <Link
          to="/gateways"
          className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium"
        >
          Cancel
        </Link>

        <button
          onClick={handleSubmit}
          disabled={submitting}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {submitting ? (
            <>
              <LoadingSpinner size="sm" />
              Creating...
            </>
          ) : (
            'Create Gateway'
          )}
        </button>
      </div>
    </div>
  );
}
