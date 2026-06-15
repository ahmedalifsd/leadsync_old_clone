import { useState, useEffect } from 'react';
import { Navbar } from '../components/Navbar';
import { api } from '../services/api';

interface AnalyticsData {
  total_leads: number;
  qualified_leads: number;
  converted_leads: number;
  conversion_rate: number;
  avg_lead_score: number;
  leads_by_status: Record<string, number>;
  leads_by_source: Record<string, number>;
  leads_by_category: Record<string, number>;
}

export const AnalyticsPage = () => {
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [timeRange, setTimeRange] = useState('30'); // days

  useEffect(() => {
    fetchAnalytics();
  }, [timeRange]);

  const fetchAnalytics = async () => {
    try {
      setLoading(true);
      const response = await api.getAnalytics({ days: parseInt(timeRange) });
      setAnalytics(response.data);
    } catch (err) {
      setError('Failed to load analytics');
      console.error('Analytics error:', err);
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
            <p className="mt-4 text-gray-600">Loading analytics...</p>
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
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold" style={{ color: '#092C4C' }}>
              Analytics & Reports
            </h1>
            <p className="text-gray-600 mt-2">Insights into your sales pipeline</p>
          </div>
          <div>
            <select
              className="input px-4 py-2"
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
            >
              <option value="7">Last 7 Days</option>
              <option value="30">Last 30 Days</option>
              <option value="90">Last 90 Days</option>
              <option value="365">Last Year</option>
            </select>
          </div>
        </div>

        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
            {error}
          </div>
        )}

        {analytics && (
          <>
            {/* Key Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
              <div className="card p-6">
                <h3 className="text-gray-600 font-medium text-sm mb-2">Total Leads</h3>
                <p className="text-3xl font-bold" style={{ color: '#092C4C' }}>
                  {analytics.total_leads}
                </p>
              </div>

              <div className="card p-6">
                <h3 className="text-gray-600 font-medium text-sm mb-2">Qualified</h3>
                <p className="text-3xl font-bold text-green-600">
                  {analytics.qualified_leads}
                </p>
              </div>

              <div className="card p-6">
                <h3 className="text-gray-600 font-medium text-sm mb-2">Converted</h3>
                <p className="text-3xl font-bold text-emerald-600">
                  {analytics.converted_leads}
                </p>
              </div>

              <div className="card p-6">
                <h3 className="text-gray-600 font-medium text-sm mb-2">Conversion Rate</h3>
                <p className="text-3xl font-bold" style={{ color: '#F39C12' }}>
                  {analytics.conversion_rate.toFixed(1)}%
                </p>
              </div>

              <div className="card p-6">
                <h3 className="text-gray-600 font-medium text-sm mb-2">Avg Score</h3>
                <p className="text-3xl font-bold" style={{ color: '#8b640d' }}>
                  {analytics.avg_lead_score.toFixed(1)}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              {/* Leads by Status */}
              <div className="card p-6">
                <h2 className="text-xl font-semibold mb-6" style={{ color: '#092C4C' }}>
                  By Status
                </h2>
                <div className="space-y-3">
                  {Object.entries(analytics.leads_by_status).map(([status, count]) => (
                    <div key={status}>
                      <div className="flex justify-between mb-1">
                        <span className="text-sm font-medium text-gray-700">{status}</span>
                        <span className="text-sm text-gray-600">{count}</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="h-2 rounded-full"
                          style={{
                            width: `${
                              analytics.total_leads > 0
                                ? (count / analytics.total_leads) * 100
                                : 0
                            }%`,
                            backgroundColor: '#8b640d',
                          }}
                        ></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Leads by Source */}
              <div className="card p-6">
                <h2 className="text-xl font-semibold mb-6" style={{ color: '#092C4C' }}>
                  By Source
                </h2>
                {Object.entries(analytics.leads_by_source).length === 0 ? (
                  <p className="text-gray-500 text-sm">No data available</p>
                ) : (
                  <div className="space-y-3">
                    {Object.entries(analytics.leads_by_source).map(([source, count]) => (
                      <div key={source} className="flex justify-between items-center">
                        <span className="text-sm text-gray-700">{source}</span>
                        <span className="font-semibold" style={{ color: '#092C4C' }}>
                          {count}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Leads by Category */}
              <div className="card p-6">
                <h2 className="text-xl font-semibold mb-6" style={{ color: '#092C4C' }}>
                  By Category
                </h2>
                {Object.entries(analytics.leads_by_category).length === 0 ? (
                  <p className="text-gray-500 text-sm">No data available</p>
                ) : (
                  <div className="space-y-3">
                    {Object.entries(analytics.leads_by_category).map(([category, count]) => (
                      <div key={category} className="flex justify-between items-center">
                        <span className="text-sm text-gray-700">{category}</span>
                        <span className="font-semibold" style={{ color: '#092C4C' }}>
                          {count}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Conversion Funnel */}
            <div className="card p-6 mt-8">
              <h2 className="text-xl font-semibold mb-6" style={{ color: '#092C4C' }}>
                Conversion Funnel
              </h2>
              <div className="space-y-4">
                {[
                  { label: 'Total Leads', value: analytics.total_leads, width: 100 },
                  {
                    label: 'Qualified',
                    value: analytics.qualified_leads,
                    width: (analytics.qualified_leads / Math.max(analytics.total_leads, 1)) * 100,
                  },
                  {
                    label: 'Converted',
                    value: analytics.converted_leads,
                    width: (analytics.converted_leads / Math.max(analytics.total_leads, 1)) * 100,
                  },
                ].map((item) => (
                  <div key={item.label}>
                    <div className="flex justify-between mb-2">
                      <span className="font-medium text-gray-700">{item.label}</span>
                      <span className="text-gray-600">{item.value}</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-8 overflow-hidden">
                      <div
                        className="h-8 rounded-full flex items-center justify-center transition-all"
                        style={{
                          width: `${item.width}%`,
                          backgroundColor: '#8b640d',
                        }}
                      >
                        {item.width > 20 && (
                          <span className="text-white text-xs font-semibold">
                            {item.width.toFixed(0)}%
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
