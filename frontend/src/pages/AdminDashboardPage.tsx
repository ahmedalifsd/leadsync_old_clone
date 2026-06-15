import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Navbar } from '../components/Navbar';
import { api } from '../services/api';

interface AdminStats {
  total_users: number;
  active_users: number;
  total_leads: number;
  total_revenue: number;
  active_subscriptions: number;
  new_users_today: number;
  new_leads_today: number;
  avg_lead_score: number;
}

interface RecentActivity {
  id: number;
  user: string;
  action: string;
  timestamp: string;
  target: string;
}

export const AdminDashboardPage = () => {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [activities, setActivities] = useState<RecentActivity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchAdminData();
  }, []);

  const fetchAdminData = async () => {
    try {
      setLoading(true);
      const [statsRes, activitiesRes] = await Promise.all([
        api.getAdminStats(),
        api.getRecentActivities(10),
      ]);
      setStats(statsRes.data);
      setActivities(activitiesRes.data);
    } catch (err) {
      setError('Failed to load admin data');
      console.error('Admin error:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading admin dashboard...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold" style={{ color: '#092C4C' }}>
            Admin Dashboard
          </h1>
          <p className="text-gray-600 mt-2">System overview and management</p>
        </div>

        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
            {error}
          </div>
        )}

        {/* Key Metrics */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            {/* Total Users */}
            <div className="card p-6">
              <div className="flex items-start justify-between mb-2">
                <h3 className="text-gray-600 font-medium">Total Users</h3>
                <span className="text-2xl">👥</span>
              </div>
              <div className="text-3xl font-bold" style={{ color: '#092C4C' }}>
                {stats.total_users}
              </div>
              <p className="text-sm text-green-600 mt-2">
                +{stats.new_users_today} today
              </p>
            </div>

            {/* Active Users */}
            <div className="card p-6">
              <div className="flex items-start justify-between mb-2">
                <h3 className="text-gray-600 font-medium">Active Users</h3>
                <span className="text-2xl">🟢</span>
              </div>
              <div className="text-3xl font-bold text-green-600">
                {stats.active_users}
              </div>
              <p className="text-sm text-gray-500 mt-2">
                {((stats.active_users / Math.max(stats.total_users, 1)) * 100).toFixed(1)}% active
              </p>
            </div>

            {/* Total Leads */}
            <div className="card p-6">
              <div className="flex items-start justify-between mb-2">
                <h3 className="text-gray-600 font-medium">Total Leads</h3>
                <span className="text-2xl">📊</span>
              </div>
              <div className="text-3xl font-bold" style={{ color: '#8b640d' }}>
                {stats.total_leads}
              </div>
              <p className="text-sm text-green-600 mt-2">
                +{stats.new_leads_today} today
              </p>
            </div>

            {/* Active Subscriptions */}
            <div className="card p-6">
              <div className="flex items-start justify-between mb-2">
                <h3 className="text-gray-600 font-medium">Subscriptions</h3>
                <span className="text-2xl">💳</span>
              </div>
              <div className="text-3xl font-bold text-blue-600">
                {stats.active_subscriptions}
              </div>
              <p className="text-sm text-gray-500 mt-2">
                Total Revenue: ${stats.total_revenue?.toLocaleString()}
              </p>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Management Section */}
          <div className="lg:col-span-2 space-y-8">
            {/* Quick Actions */}
            <div className="card p-6">
              <h2 className="text-xl font-bold mb-6" style={{ color: '#092C4C' }}>
                Quick Actions
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Link
                  to="/admin/users"
                  className="card p-4 hover:shadow-lg transition-shadow cursor-pointer border-2 border-transparent hover:border-primary"
                >
                  <h3 className="font-semibold text-gray-900">Manage Users</h3>
                  <p className="text-sm text-gray-600 mt-1">View and manage user accounts</p>
                </Link>

                <Link
                  to="/admin/teams"
                  className="card p-4 hover:shadow-lg transition-shadow cursor-pointer border-2 border-transparent hover:border-primary"
                >
                  <h3 className="font-semibold text-gray-900">Manage Teams</h3>
                  <p className="text-sm text-gray-600 mt-1">Create and manage teams</p>
                </Link>

                <Link
                  to="/admin/subscriptions"
                  className="card p-4 hover:shadow-lg transition-shadow cursor-pointer border-2 border-transparent hover:border-primary"
                >
                  <h3 className="font-semibold text-gray-900">Subscriptions</h3>
                  <p className="text-sm text-gray-600 mt-1">Manage user subscriptions</p>
                </Link>

                <Link
                  to="/admin/billing"
                  className="card p-4 hover:shadow-lg transition-shadow cursor-pointer border-2 border-transparent hover:border-primary"
                >
                  <h3 className="font-semibold text-gray-900">Billing & Invoices</h3>
                  <p className="text-sm text-gray-600 mt-1">View payments and invoices</p>
                </Link>

                <Link
                  to="/admin/reports"
                  className="card p-4 hover:shadow-lg transition-shadow cursor-pointer border-2 border-transparent hover:border-primary"
                >
                  <h3 className="font-semibold text-gray-900">Reports</h3>
                  <p className="text-sm text-gray-600 mt-1">Generate system reports</p>
                </Link>

                <Link
                  to="/admin/settings"
                  className="card p-4 hover:shadow-lg transition-shadow cursor-pointer border-2 border-transparent hover:border-primary"
                >
                  <h3 className="font-semibold text-gray-900">System Settings</h3>
                  <p className="text-sm text-gray-600 mt-1">Configure system settings</p>
                </Link>
              </div>
            </div>

            {/* Recent Activities */}
            <div className="card p-6">
              <h2 className="text-xl font-bold mb-4" style={{ color: '#092C4C' }}>
                Recent Activities
              </h2>
              {activities.length === 0 ? (
                <p className="text-gray-500 text-sm">No recent activities</p>
              ) : (
                <div className="space-y-3">
                  {activities.map((activity) => (
                    <div
                      key={activity.id}
                      className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                    >
                      <div>
                        <p className="font-medium text-gray-900">{activity.user}</p>
                        <p className="text-sm text-gray-600">
                          {activity.action} {activity.target}
                        </p>
                      </div>
                      <p className="text-xs text-gray-500">
                        {new Date(activity.timestamp).toLocaleTimeString()}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* System Status */}
          <div className="space-y-6">
            {/* System Health */}
            <div className="card p-6">
              <h2 className="text-xl font-bold mb-4" style={{ color: '#092C4C' }}>
                System Status
              </h2>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-gray-700">API Status</span>
                  <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full font-semibold">
                    Healthy
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-700">Database</span>
                  <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full font-semibold">
                    Connected
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-700">Cache</span>
                  <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full font-semibold">
                    Active
                  </span>
                </div>
              </div>
            </div>

            {/* System Info */}
            <div className="card p-6">
              <h2 className="text-lg font-bold mb-4" style={{ color: '#092C4C' }}>
                System Info
              </h2>
              <div className="space-y-3 text-sm">
                <div>
                  <p className="text-gray-600">Version</p>
                  <p className="font-semibold">1.0.0</p>
                </div>
                <div>
                  <p className="text-gray-600">Last Updated</p>
                  <p className="font-semibold">{new Date().toLocaleDateString()}</p>
                </div>
                <div>
                  <p className="text-gray-600">Environment</p>
                  <p className="font-semibold">Production</p>
                </div>
              </div>
            </div>

            {/* Help */}
            <div className="card p-6 bg-blue-50 border border-blue-200">
              <h3 className="font-semibold text-blue-900 mb-2">Need Help?</h3>
              <p className="text-sm text-blue-700 mb-3">
                Check the documentation or contact support for assistance.
              </p>
              <button className="text-blue-600 hover:text-blue-800 text-sm font-medium">
                View Docs →
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
