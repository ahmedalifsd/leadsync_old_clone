import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { Navbar } from '../components/Navbar';
import { api } from '../services/api';
import type { Lead } from '../types';

export const LeadDetailPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [lead, setLead] = useState<Lead | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (id) {
      fetchLead(parseInt(id));
    }
  }, [id]);

  const fetchLead = async (leadId: number) => {
    try {
      setLoading(true);
      const response = await api.getLead(leadId);
      setLead(response.data);
    } catch (err) {
      setError('Failed to load lead details');
      console.error('Lead detail error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this lead?')) return;

    try {
      if (id) {
        await api.deleteLead(parseInt(id));
        navigate('/leads');
      }
    } catch (err) {
      setError('Failed to delete lead');
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

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading lead details...</p>
          </div>
        </div>
      </div>
    );
  }

  if (!lead) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="max-w-7xl mx-auto px-4 py-8">
          <div className="text-center py-12">
            <h1 className="text-2xl font-bold text-gray-900">Lead not found</h1>
            <Link to="/leads" className="btn-primary mt-4 inline-block">
              Back to Leads
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="flex justify-between items-start mb-8">
          <div>
            <h1 className="text-3xl font-bold" style={{ color: '#092C4C' }}>
              {lead.client_name}
            </h1>
            <p className="text-gray-600 mt-2">Lead ID: {lead.id}</p>
          </div>
          <div className="flex gap-2">
            <Link to={`/leads/${lead.id}/edit`} className="btn-outline">
              Edit
            </Link>
            <button onClick={handleDelete} className="btn-outline text-red-600 border-red-200">
              Delete
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Status & Score */}
            <div className="card p-6">
              <h2 className="text-xl font-semibold mb-4" style={{ color: '#092C4C' }}>
                Status & Score
              </h2>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-600 mb-1">Status</p>
                  <span
                    className={`inline-block px-3 py-1 rounded-full text-sm font-semibold ${getStatusColor(
                      lead.status
                    )}`}
                  >
                    {getStatusLabel(lead.status)}
                  </span>
                </div>
                <div>
                  <p className="text-sm text-gray-600 mb-1">Lead Score</p>
                  <p className="text-2xl font-bold" style={{ color: '#8b640d' }}>
                    {lead.lead_score}
                  </p>
                </div>
              </div>
              <div className="mt-4">
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="h-2 rounded-full"
                    style={{
                      width: `${Math.min(lead.lead_score, 100)}%`,
                      backgroundColor: '#8b640d',
                    }}
                  ></div>
                </div>
              </div>
            </div>

            {/* Contact Information */}
            <div className="card p-6">
              <h2 className="text-xl font-semibold mb-4" style={{ color: '#092C4C' }}>
                Contact Information
              </h2>
              <div className="space-y-3">
                {lead.email && (
                  <div>
                    <p className="text-sm text-gray-600">Email</p>
                    <a
                      href={`mailto:${lead.email}`}
                      className="text-primary hover:underline"
                    >
                      {lead.email}
                    </a>
                  </div>
                )}
                {lead.contact_number && (
                  <div>
                    <p className="text-sm text-gray-600">Phone</p>
                    <a
                      href={`tel:${lead.contact_number}`}
                      className="text-primary hover:underline"
                    >
                      {lead.contact_number}
                    </a>
                  </div>
                )}
              </div>
            </div>

            {/* Details */}
            <div className="card p-6">
              <h2 className="text-xl font-semibold mb-4" style={{ color: '#092C4C' }}>
                Details
              </h2>
              <div className="space-y-4">
                {lead.requirement && (
                  <div>
                    <p className="text-sm font-semibold text-gray-700 mb-1">
                      Requirements
                    </p>
                    <p className="text-gray-600">{lead.requirement}</p>
                  </div>
                )}
                {lead.notes && (
                  <div>
                    <p className="text-sm font-semibold text-gray-700 mb-1">
                      Notes
                    </p>
                    <p className="text-gray-600">{lead.notes}</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Key Information */}
            <div className="card p-6">
              <h2 className="text-lg font-semibold mb-4" style={{ color: '#092C4C' }}>
                Key Information
              </h2>
              <div className="space-y-3">
                <div>
                  <p className="text-sm text-gray-600">Category</p>
                  <p className="font-medium">{lead.category || 'Not specified'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Source</p>
                  <p className="font-medium">{lead.source || 'Not specified'}</p>
                </div>
                {lead.budget && (
                  <div>
                    <p className="text-sm text-gray-600">Budget</p>
                    <p className="font-medium">${lead.budget}</p>
                  </div>
                )}
                {lead.decision_maker && (
                  <div className="bg-blue-50 px-3 py-2 rounded border border-blue-200">
                    <p className="text-sm text-blue-800">
                      ✓ Decision Maker
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Dates */}
            <div className="card p-6">
              <h2 className="text-lg font-semibold mb-4" style={{ color: '#092C4C' }}>
                Timeline
              </h2>
              <div className="space-y-3 text-sm">
                <div>
                  <p className="text-gray-600">Created</p>
                  <p className="font-medium">
                    {new Date(lead.created_at).toLocaleDateString()}
                  </p>
                </div>
                {lead.follow_up_date && (
                  <div>
                    <p className="text-gray-600">Follow-up</p>
                    <p className="font-medium">{lead.follow_up_date}</p>
                  </div>
                )}
                {lead.conversion_date && (
                  <div>
                    <p className="text-gray-600">Converted</p>
                    <p className="font-medium">
                      {new Date(lead.conversion_date).toLocaleDateString()}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Back Button */}
        <div className="mt-8">
          <Link to="/leads" className="btn-outline">
            ← Back to Leads
          </Link>
        </div>
      </div>
    </div>
  );
};
