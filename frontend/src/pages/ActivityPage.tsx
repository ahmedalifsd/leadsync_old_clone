import { useState, useEffect } from 'react';
import { Navbar } from '../components/Navbar';
import { api } from '../services/api';

interface Activity {
  id: number;
  user: string;
  action: string;
  target_model: string;
  target_name: string;
  target_id: number;
  details: string;
  timestamp: string;
}

export const ActivityPage = () => {
  const [activities, setActivities] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [filters, setFilters] = useState({ action: '', model: '' });

  useEffect(() => {
    fetchActivities();
  }, [page, filters]);

  const fetchActivities = async () => {
    try {
      setLoading(true);
      const response = await api.getActivityLogs(page, {
        action: filters.action || undefined,
        target_model: filters.model || undefined,
      });
      setActivities(response.data.results || response.data);
      setTotalPages(response.data.total_pages || 1);
    } catch (err) {
      setError('Failed to load activities');
      console.error('Activity error:', err);
    } finally {
      setLoading(false);
    }
  };

  const ACTION_COLORS: Record<string, string> = {
    create: 'bg-green-100 text-green-800',
    update: 'bg-blue-100 text-blue-800',
    delete: 'bg-red-100 text-red-800',
    view: 'bg-gray-100 text-gray-800',
    import: 'bg-purple-100 text-purple-800',
    export: 'bg-orange-100 text-orange-800',
    login: 'bg-indigo-100 text-indigo-800',
    logout: 'bg-slate-100 text-slate-800',
  };

  const getActionColor = (action: string) => {
    return ACTION_COLORS[action] || 'bg-gray-100 text-gray-800';
  };

  const formatAction = (action: string) => {
    return action.charAt(0).toUpperCase() + action.slice(1);
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor(diff / (1000 * 60));
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    return date.toLocaleDateString();
  };

  if (loading && activities.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading activity log...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold" style={{ color: '#092C4C' }}>
            Activity Log
          </h1>
          <p className="text-gray-600 mt-2">View all your account activities</p>
        </div>

        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
            {error}
          </div>
        )}

        {/* Filters */}
        <div className="card p-6 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="label">Action Type</label>
              <select
                className="input"
                value={filters.action}
                onChange={(e) => {
                  setFilters({ ...filters, action: e.target.value });
                  setPage(1);
                }}
              >
                <option value="">All Actions</option>
                <option value="create">Create</option>
                <option value="update">Update</option>
                <option value="delete">Delete</option>
                <option value="view">View</option>
                <option value="import">Import</option>
                <option value="export">Export</option>
                <option value="login">Login</option>
                <option value="logout">Logout</option>
              </select>
            </div>

            <div>
              <label className="label">Target Model</label>
              <select
                className="input"
                value={filters.model}
                onChange={(e) => {
                  setFilters({ ...filters, model: e.target.value });
                  setPage(1);
                }}
              >
                <option value="">All Models</option>
                <option value="Lead">Lead</option>
                <option value="LeadTemplate">Template</option>
                <option value="User">User</option>
                <option value="Category">Category</option>
                <option value="Source">Source</option>
              </select>
            </div>

            <div className="flex items-end">
              <button
                className="btn-outline w-full"
                onClick={() => {
                  setFilters({ action: '', model: '' });
                  setPage(1);
                }}
              >
                Clear Filters
              </button>
            </div>
          </div>
        </div>

        {/* Activity Timeline */}
        <div className="card overflow-hidden">
          {activities.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <p className="text-lg">No activities found</p>
              <p className="text-sm mt-2">Your activities will appear here</p>
            </div>
          ) : (
            <div className="divide-y">
              {activities.map((activity) => (
                <div
                  key={activity.id}
                  className="p-6 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <span
                        className={`px-3 py-1 rounded-full text-xs font-semibold ${getActionColor(
                          activity.action
                        )}`}
                      >
                        {formatAction(activity.action)}
                      </span>
                      <span className="text-sm text-gray-600">
                        {activity.target_name || activity.target_model}
                      </span>
                    </div>
                    <span className="text-xs text-gray-500">
                      {formatDate(activity.timestamp)}
                    </span>
                  </div>

                  <div className="ml-24 space-y-1">
                    <p className="text-sm text-gray-700">
                      <span className="font-medium">{formatAction(activity.action)}</span>
                      {' '}{activity.target_model.toLowerCase()}
                      {activity.target_name && (
                        <>
                          {' '}
                          <span className="font-medium">{activity.target_name}</span>
                        </>
                      )}
                    </p>

                    {activity.details && (
                      <p className="text-xs text-gray-500 mt-2">
                        {activity.details}
                      </p>
                    )}

                    <p className="text-xs text-gray-400 mt-2">
                      {new Date(activity.timestamp).toLocaleString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="bg-gray-50 px-6 py-4 border-t flex justify-center gap-2">
              <button
                disabled={page === 1}
                onClick={() => setPage(page - 1)}
                className="px-3 py-1 border rounded text-sm hover:bg-white disabled:opacity-50"
              >
                Previous
              </button>
              {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => i + 1).map((p) => (
                <button
                  key={p}
                  onClick={() => setPage(p)}
                  className={`px-3 py-1 border rounded text-sm ${
                    page === p ? 'bg-primary text-white' : 'hover:bg-white'
                  }`}
                >
                  {p}
                </button>
              ))}
              <button
                disabled={page === totalPages}
                onClick={() => setPage(page + 1)}
                className="px-3 py-1 border rounded text-sm hover:bg-white disabled:opacity-50"
              >
                Next
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
