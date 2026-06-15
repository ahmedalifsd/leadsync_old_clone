import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Navbar } from '../components/Navbar';
import { api } from '../services/api';

interface Template {
  id: number;
  name: string;
  category?: string;
  source?: string;
  status: string;
  notes: string;
  created_at: string;
}

export const TemplatesPage = () => {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    category: '',
    source: '',
    status: 'new',
    notes: '',
  });
  const navigate = useNavigate();

  useEffect(() => {
    fetchTemplates();
  }, []);

  const fetchTemplates = async () => {
    try {
      setLoading(true);
      const response = await api.getLeadTemplates();
      setTemplates(response.data.results || response.data);
    } catch (err) {
      setError('Failed to load templates');
      console.error('Templates error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.name.trim()) {
      setError('Template name is required');
      return;
    }

    try {
      if (editingId) {
        await api.updateLeadTemplate(editingId, formData);
        setTemplates(
          templates.map((t) =>
            t.id === editingId ? { ...t, ...formData } : t
          )
        );
      } else {
        const response = await api.createLeadTemplate(formData);
        setTemplates([...templates, response.data]);
      }
      resetForm();
      fetchTemplates();
    } catch (err) {
      setError('Failed to save template');
      console.error('Template save error:', err);
    }
  };

  const handleEdit = (template: Template) => {
    setFormData({
      name: template.name,
      category: template.category || '',
      source: template.source || '',
      status: template.status,
      notes: template.notes,
    });
    setEditingId(template.id);
    setShowForm(true);
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Are you sure you want to delete this template?')) return;

    try {
      await api.deleteLeadTemplate(id);
      setTemplates(templates.filter((t) => t.id !== id));
    } catch (err) {
      setError('Failed to delete template');
    }
  };

  const handleUseTemplate = (template: Template) => {
    // Navigate to add lead page with template data in state
    navigate('/leads/add', {
      state: {
        template: {
          category: template.category,
          source: template.source,
          status: template.status,
          notes: template.notes,
        },
      },
    });
  };

  const resetForm = () => {
    setFormData({
      name: '',
      category: '',
      source: '',
      status: 'new',
      notes: '',
    });
    setEditingId(null);
    setShowForm(false);
  };

  const getStatusLabel = (status: string) => {
    const labels: Record<string, string> = {
      new: 'New',
      not_contacted: 'Not Contacted',
      contacted: 'Contacted',
      no_response: 'No Response',
      interested: 'Interested',
      not_interested: 'Not Interested',
      qualified: 'Qualified',
      proposal: 'Proposal Sent',
      negotiation: 'Negotiation',
      won: 'Won',
      lost: 'Lost',
    };
    return labels[status] || status;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading templates...</p>
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
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold" style={{ color: '#092C4C' }}>
              Lead Templates
            </h1>
            <p className="text-gray-600 mt-2">Create and manage lead templates</p>
          </div>
          <button
            onClick={() => setShowForm(!showForm)}
            className="btn-primary"
          >
            {showForm ? 'Cancel' : 'New Template'}
          </button>
        </div>

        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
            {error}
          </div>
        )}

        {/* Form */}
        {showForm && (
          <div className="card p-6 mb-6">
            <h2 className="text-xl font-semibold mb-4" style={{ color: '#092C4C' }}>
              {editingId ? 'Edit Template' : 'Create New Template'}
            </h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="form-group">
                  <label htmlFor="name" className="label">
                    Template Name *
                  </label>
                  <input
                    type="text"
                    id="name"
                    name="name"
                    value={formData.name}
                    onChange={handleChange}
                    className="input"
                    placeholder="e.g., Web Service Prospect"
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="status" className="label">
                    Initial Status
                  </label>
                  <select
                    id="status"
                    name="status"
                    value={formData.status}
                    onChange={handleChange}
                    className="input"
                  >
                    <option value="new">New</option>
                    <option value="not_contacted">Not Contacted</option>
                    <option value="contacted">Contacted</option>
                    <option value="interested">Interested</option>
                    <option value="qualified">Qualified</option>
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="category" className="label">
                    Category
                  </label>
                  <select
                    id="category"
                    name="category"
                    value={formData.category}
                    onChange={handleChange}
                    className="input"
                  >
                    <option value="">Select category</option>
                    <option value="product">Product</option>
                    <option value="service">Service</option>
                    <option value="consultation">Consultation</option>
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="source" className="label">
                    Source
                  </label>
                  <select
                    id="source"
                    name="source"
                    value={formData.source}
                    onChange={handleChange}
                    className="input"
                  >
                    <option value="">Select source</option>
                    <option value="website">Website</option>
                    <option value="referral">Referral</option>
                    <option value="social_media">Social Media</option>
                    <option value="email">Email</option>
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="notes" className="label">
                  Default Notes
                </label>
                <textarea
                  id="notes"
                  name="notes"
                  value={formData.notes}
                  onChange={handleChange}
                  className="input resize-none"
                  rows={4}
                  placeholder="Add default notes for this template"
                />
              </div>

              <div className="flex gap-2">
                <button type="submit" className="btn-primary">
                  {editingId ? 'Update Template' : 'Create Template'}
                </button>
                <button
                  type="button"
                  onClick={resetForm}
                  className="btn-outline"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Templates Grid */}
        {templates.length === 0 ? (
          <div className="card p-12 text-center">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              No templates yet
            </h3>
            <p className="text-gray-600 mb-4">
              Create your first template to save time when adding leads
            </p>
            <button
              onClick={() => setShowForm(true)}
              className="btn-primary inline-block"
            >
              Create Your First Template
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {templates.map((template) => (
              <div key={template.id} className="card p-6">
                <div className="flex justify-between items-start mb-3">
                  <h3 className="text-lg font-semibold" style={{ color: '#092C4C' }}>
                    {template.name}
                  </h3>
                  <span className="text-xs px-2 py-1 rounded bg-blue-100 text-blue-800">
                    {getStatusLabel(template.status)}
                  </span>
                </div>

                {(template.category || template.source) && (
                  <div className="mb-3 text-sm text-gray-600 space-y-1">
                    {template.category && (
                      <p>
                        <span className="font-medium">Category:</span> {template.category}
                      </p>
                    )}
                    {template.source && (
                      <p>
                        <span className="font-medium">Source:</span> {template.source}
                      </p>
                    )}
                  </div>
                )}

                {template.notes && (
                  <p className="text-sm text-gray-600 mb-4 line-clamp-3">
                    {template.notes}
                  </p>
                )}

                <p className="text-xs text-gray-500 mb-4">
                  Created {new Date(template.created_at).toLocaleDateString()}
                </p>

                <div className="flex gap-2">
                  <button
                    onClick={() => handleUseTemplate(template)}
                    className="flex-1 btn-primary text-sm py-2"
                  >
                    Use Template
                  </button>
                  <button
                    onClick={() => handleEdit(template)}
                    className="px-3 py-2 text-sm border rounded hover:bg-gray-50"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(template.id)}
                    className="px-3 py-2 text-sm border border-red-200 text-red-600 rounded hover:bg-red-50"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
