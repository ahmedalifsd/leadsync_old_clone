import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { Navbar } from '../components/Navbar';

interface DashboardStats {
  total_leads: number;
  new_leads: number;
  contacted_leads: number;
  qualified_leads: number;
  converted_leads: number;
  leads_needing_followup: number;
  conversion_rate: number;
  avg_lead_score: number;
}

interface StatusDistribution {
  status: string;
  count: number;
  percentage: number;
}

export const DashboardPage = () => {
  const { user } = useAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [statusDistribution, setStatusDistribution] = useState<StatusDistribution[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        const [statsRes, statusRes] = await Promise.all([
          api.getDashboardStats(),
          api.getLeadStatusDistribution(),
        ]);
        setStats(statsRes.data);
        setStatusDistribution(statusRes.data);
      } catch (err) {
        setError('Failed to load dashboard data');
        console.error('Dashboard error:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading dashboard...</p>
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
            Welcome back, {user?.first_name || user?.username}!
          </h1>
          <p className="text-gray-600 mt-2">Here&apos;s an overview of your leads</p>
        </div>

        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
            {error}
          </div>
        )}

        {/* Key Metrics */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            {/* Total Leads */}
            <div className="card p-6">
              <div className="flex items-start justify-between mb-2">
                <h3 className="text-gray-600 font-medium">Total Leads</h3>
                <span className="text-2xl">📊</span>
              </div>
              <div className="text-3xl font-bold" style={{ color: '#092C4C' }}>
                {stats.total_leads}
              </div>
              <p className="text-sm text-gray-500 mt-2">All your leads</p>
            </div>

            {/* New Leads */}
            <div className="card p-6">
              <div className="flex items-start justify-between mb-2">
                <h3 className="text-gray-600 font-medium">New Leads</h3>
                <span className="text-2xl">✨</span>
              </div>
              <div className="text-3xl font-bold" style={{ color: '#8b640d' }}>
                {stats.new_leads}
              </div>
              <p className="text-sm text-gray-500 mt-2">In the last 7 days</p>
            </div>

            {/* Qualified Leads */}
            <div className="card p-6">
              <div className="flex items-start justify-between mb-2">
                <h3 className="text-gray-600 font-medium">Qualified Leads</h3>
                <span className="text-2xl">⭐</span>
              </div>
              <div className="text-3xl font-bold text-success">
                {stats.qualified_leads}
              </div>
              <p className="text-sm text-gray-500 mt-2">Ready to convert</p>
            </div>

            {/* Conversion Rate */}
            <div className="card p-6">
              <div className="flex items-start justify-between mb-2">
                <h3 className="text-gray-600 font-medium">Conversion Rate</h3>
                <span className="text-2xl">🎯</span>
              </div>
              <div className="text-3xl font-bold" style={{ color: '#F39C12' }}>
                {stats.conversion_rate.toFixed(1)}%
              </div>
              <p className="text-sm text-gray-500 mt-2">Overall conversion</p>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Status Distribution */}
          <div className="lg:col-span-2">
            <div className="card p-6">
              <h2 className="text-xl font-bold mb-6" style={{ color: '#092C4C' }}>
                Lead Status Distribution
              </h2>

              {statusDistribution.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <p>No leads yet. Start by adding your first lead!</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {statusDistribution.map((status) => (
                    <div key={status.status}>
                      <div className="flex justify-between mb-1">
                        <span className="font-medium text-gray-700">
                          {status.status}
                        </span>
                        <span className="text-gray-600">
                          {status.count} ({status.percentage}%)
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="h-2 rounded-full transition-all"
                          style={{
                            width: `${status.percentage}%`,
                            backgroundColor: '#8b640d',
                          }}
                        ></div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Quick Actions */}
          <div>
            <div className="card p-6">
              <h2 className="text-xl font-bold mb-6" style={{ color: '#092C4C' }}>
                Quick Actions
              </h2>

              <div className="space-y-3">
                <Link
                  to="/leads/add"
                  className="btn-primary w-full py-2 px-4 text-center block rounded-lg font-medium"
                >
                  Add New Lead
                </Link>

                <Link
                  to="/leads"
                  className="btn-outline w-full py-2 px-4 text-center block rounded-lg font-medium"
                >
                  View All Leads
                </Link>

                <button
                  className="w-full py-2 px-4 text-center rounded-lg font-medium text-gray-700 hover:bg-gray-100 border border-gray-300"
                  onClick={() => alert('Import feature coming soon!')}
                >
                  Import Leads
                </button>

                <button
                  className="w-full py-2 px-4 text-center rounded-lg font-medium text-gray-700 hover:bg-gray-100 border border-gray-300"
                  onClick={() => alert('Analytics coming soon!')}
                >
                  View Analytics
                </button>
              </div>
            </div>

            {/* Recent Activity */}
            <div className="card p-6 mt-6">
              <h2 className="text-xl font-bold mb-4" style={{ color: '#092C4C' }}>
                Recent Activity
              </h2>
              <div className="text-center py-8 text-gray-500">
                <p className="text-sm">Activity logs coming soon</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
