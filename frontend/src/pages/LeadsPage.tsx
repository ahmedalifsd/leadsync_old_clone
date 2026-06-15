import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Navbar } from '../components/Navbar';
import { api } from '../services/api';
import type { Lead } from '../types';

export const LeadsPage = () => {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [filters, setFilters] = useState({ status: '', search: '' });
  const navigate = useNavigate();

  useEffect(() => {
    fetchLeads();
  }, [page, filters]);

  const fetchLeads = async () => {
    try {
      setLoading(true);
      const response = await api.getLeads(page, {
        status: filters.status || undefined,
        search: filters.search || undefined,
      });
      setLeads(response.data.results || response.data);
      setTotalPages(response.data.total_pages || 1);
    } catch (err) {
      setError('Failed to load leads');
      console.error('Leads error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Are you sure you want to delete this lead?')) return;

    try {
      await api.deleteLead(id);
      setLeads(leads.filter((lead) => lead.id !== id));
    } catch (err) {
      setError('Failed to delete lead');
    }
  };

  const handleStatusChange = async (id: number, newStatus: string) => {
    try {
      await api.partialUpdateLead(id, { status: newStatus });
      setLeads(
        leads.map((lead) =>
          lead.id === id ? { ...lead, status: newStatus } : lead
        )
      );
    } catch (err) {
      setError('Failed to update lead status');
    }
  };

  const STATUS_OPTIONS = [
    { value: 'new', label: 'New', color: 'bg-blue-100 text-blue-800' },
    { value: 'not_contacted', label: 'Not Contacted', color: 'bg-gray-100 text-gray-800' },
    { value: 'contacted', label: 'Contacted', color: 'bg-yellow-100 text-yellow-800' },
    { value: 'no_response', label: 'No Response', color: 'bg-orange-100 text-orange-800' },
    { value: 'interested', label: 'Interested', color: 'bg-blue-100 text-blue-800' },
    { value: 'not_interested', label: 'Not Interested', color: 'bg-red-100 text-red-800' },
    { value: 'qualified', label: 'Qualified', color: 'bg-green-100 text-green-800' },
    { value: 'proposal', label: 'Proposal Sent', color: 'bg-indigo-100 text-indigo-800' },
    { value: 'negotiation', label: 'Negotiation', color: 'bg-purple-100 text-purple-800' },
    { value: 'won', label: 'Won', color: 'bg-emerald-100 text-emerald-800' },
    { value: 'lost', label: 'Lost', color: 'bg-slate-100 text-slate-800' },
  ];

  const getStatusColor = (status: string) => {
    const statusOption = STATUS_OPTIONS.find((s) => s.value === status);
    return statusOption?.color || 'bg-gray-100 text-gray-800';
  };

  const getStatusLabel = (status: string) => {
    const statusOption = STATUS_OPTIONS.find((s) => s.value === status);
    return statusOption?.label || status;
  };

  if (loading && leads.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading leads...</p>
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
              Leads
            </h1>
            <p className="text-gray-600 mt-1">Manage and track your leads</p>
          </div>
          <Link to="/leads/add" className="btn-primary">
            Add New Lead
          </Link>
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
              <label className="label">Search</label>
              <input
                type="text"
                className="input"
                placeholder="Search by name, email, or phone..."
                value={filters.search}
                onChange={(e) => {
                  setFilters({ ...filters, search: e.target.value });
                  setPage(1);
                }}
              />
            </div>

            <div>
              <label className="label">Status</label>
              <select
                className="input"
                value={filters.status}
                onChange={(e) => {
                  setFilters({ ...filters, status: e.target.value });
                  setPage(1);
                }}
              >
                <option value="">All Statuses</option>
                {STATUS_OPTIONS.map((status) => (
                  <option key={status.value} value={status.value}>
                    {status.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-end">
              <button
                className="btn-outline w-full"
                onClick={() => {
                  setFilters({ status: '', search: '' });
                  setPage(1);
                }}
              >
                Clear Filters
              </button>
            </div>
          </div>
        </div>

        {/* Leads Table */}
        <div className="card overflow-hidden">
          {leads.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <p className="text-lg">No leads found</p>
              <p className="text-sm mt-2">Start by adding your first lead</p>
              <Link to="/leads/add" className="btn-primary mt-4 inline-block">
                Add Your First Lead
              </Link>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 border-b" style={{ borderColor: '#e5e7eb' }}>
                    <tr>
                      <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">
                        Name
                      </th>
                      <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">
                        Contact
                      </th>
                      <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">
                        Score
                      </th>
                      <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">
                        Created
                      </th>
                      <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {leads.map((lead) => (
                      <tr
                        key={lead.id}
                        className="border-b hover:bg-gray-50 transition-colors"
                      >
                        <td className="px-6 py-4">
                          <Link
                            to={`/leads/${lead.id}`}
                            className="font-medium text-primary hover:underline"
                          >
                            {lead.client_name}
                          </Link>
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-600">
                          {lead.email || lead.contact_number || '-'}
                        </td>
                        <td className="px-6 py-4">
                          <select
                            className={`px-3 py-1 rounded-full text-xs font-semibold border-0 cursor-pointer ${getStatusColor(
                              lead.status
                            )}`}
                            value={lead.status}
                            onChange={(e) =>
                              handleStatusChange(lead.id, e.target.value)
                            }
                          >
                            {STATUS_OPTIONS.map((status) => (
                              <option
                                key={status.value}
                                value={status.value}
                              >
                                {status.label}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td className="px-6 py-4 text-sm">
                          <div className="flex items-center">
                            <div className="w-full bg-gray-200 rounded-full h-2 max-w-xs">
                              <div
                                className="h-2 rounded-full"
                                style={{
                                  width: `${Math.min(lead.lead_score, 100)}%`,
                                  backgroundColor: '#8b640d',
                                }}
                              ></div>
                            </div>
                            <span className="ml-2 text-xs text-gray-600">
                              {lead.lead_score}
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-600">
                          {new Date(lead.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-6 py-4 text-sm">
                          <div className="flex space-x-2">
                            <button
                              onClick={() => navigate(`/leads/${lead.id}`)}
                              className="text-blue-600 hover:text-blue-800"
                            >
                              View
                            </button>
                            <button
                              onClick={() => navigate(`/leads/${lead.id}/edit`)}
                              className="text-orange-600 hover:text-orange-800"
                            >
                              Edit
                            </button>
                            <button
                              onClick={() => handleDelete(lead.id)}
                              className="text-red-600 hover:text-red-800"
                            >
                              Delete
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

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
                  {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
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
            </>
          )}
        </div>
      </div>
    </div>
  );
};
