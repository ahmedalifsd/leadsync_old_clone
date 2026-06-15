import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Navbar } from '../components/Navbar';
import { api } from '../services/api';
import type { Lead } from '../types';

interface LeadFormData {
  client_name: string;
  email: string;
  contact_number: string;
  category: string;
  category_other: string;
  source: string;
  source_other: string;
  requirement: string;
  status: string;
  budget: string;
  timeline: string;
  decision_maker: boolean;
  notes: string;
  follow_up_date: string;
}

export const EditLeadPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [formData, setFormData] = useState<LeadFormData | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (id) {
      fetchLead(parseInt(id));
    }
  }, [id]);

  const fetchLead = async (leadId: number) => {
    try {
      setLoading(true);
      const response = await api.getLead(leadId);
      const lead: Lead = response.data;
      setFormData({
        client_name: lead.client_name || '',
        email: lead.email || '',
        contact_number: lead.contact_number || '',
        category: lead.category || '',
        category_other: lead.category_other || '',
        source: lead.source || '',
        source_other: lead.source_other || '',
        requirement: lead.requirement || '',
        status: lead.status || 'new',
        budget: lead.budget ? String(lead.budget) : '',
        timeline: lead.timeline || '',
        decision_maker: lead.decision_maker || false,
        notes: lead.notes || '',
        follow_up_date: lead.follow_up_date || '',
      });
    } catch (err) {
      console.error('Failed to load lead:', err);
      navigate('/leads');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (
    e: React.ChangeEvent<
      HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
    >
  ) => {
    if (!formData) return;

    const { name, value, type } = e.target;
    setFormData((prev) =>
      prev
        ? {
            ...prev,
            [name]:
              type === 'checkbox'
                ? (e.target as HTMLInputElement).checked
                : value,
          }
        : null
    );

    if (errors[name]) {
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[name];
        return newErrors;
      });
    }
  };

  const validateForm = () => {
    if (!formData) return {};
    const newErrors: Record<string, string> = {};

    if (!formData.client_name.trim()) {
      newErrors.client_name = 'Lead name is required';
    }

    if (
      formData.email &&
      !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)
    ) {
      newErrors.email = 'Please enter a valid email';
    }

    return newErrors;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData || !id) return;

    const newErrors = validateForm();
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    setSaving(true);
    try {
      const submitData = {
        ...formData,
        budget: formData.budget ? parseFloat(formData.budget) : null,
      };

      await api.updateLead(parseInt(id), submitData);
      navigate(`/leads/${id}`);
    } catch (err) {
      console.error('Failed to update lead:', err);
      setErrors({
        submit: 'Failed to update lead. Please try again.',
      });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading lead...</p>
          </div>
        </div>
      </div>
    );
  }

  if (!formData) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="max-w-7xl mx-auto px-4 py-8">
          <div className="text-center py-12">
            <h1 className="text-2xl font-bold text-gray-900">Lead not found</h1>
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
        <div className="mb-8">
          <h1 className="text-3xl font-bold" style={{ color: '#092C4C' }}>
            Edit Lead
          </h1>
          <p className="text-gray-600 mt-2">Update {formData.client_name}&apos;s information</p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="card p-8 space-y-8">
          {errors.submit && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
              {errors.submit}
            </div>
          )}

          {/* Basic Information */}
          <div>
            <h2 className="text-xl font-semibold mb-4" style={{ color: '#092C4C' }}>
              Basic Information
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="form-group">
                <label htmlFor="client_name" className="label">
                  Lead Name *
                </label>
                <input
                  type="text"
                  id="client_name"
                  name="client_name"
                  value={formData.client_name}
                  onChange={handleChange}
                  className={errors.client_name ? 'input-error' : 'input'}
                  placeholder="Enter lead name"
                  disabled={saving}
                  required
                />
                {errors.client_name && (
                  <p className="text-error text-sm mt-1">{errors.client_name}</p>
                )}
              </div>

              <div className="form-group">
                <label htmlFor="email" className="label">
                  Email
                </label>
                <input
                  type="email"
                  id="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  className={errors.email ? 'input-error' : 'input'}
                  placeholder="Enter email address"
                  disabled={saving}
                />
                {errors.email && (
                  <p className="text-error text-sm mt-1">{errors.email}</p>
                )}
              </div>

              <div className="form-group">
                <label htmlFor="contact_number" className="label">
                  Phone Number
                </label>
                <input
                  type="tel"
                  id="contact_number"
                  name="contact_number"
                  value={formData.contact_number}
                  onChange={handleChange}
                  className="input"
                  placeholder="Enter phone number"
                  disabled={saving}
                />
              </div>

              <div className="form-group">
                <label htmlFor="status" className="label">
                  Status
                </label>
                <select
                  id="status"
                  name="status"
                  value={formData.status}
                  onChange={handleChange}
                  className="input"
                  disabled={saving}
                >
                  <option value="new">New</option>
                  <option value="not_contacted">Not Contacted</option>
                  <option value="contacted">Contacted</option>
                  <option value="no_response">No Response</option>
                  <option value="interested">Interested</option>
                  <option value="not_interested">Not Interested</option>
                  <option value="qualified">Qualified</option>
                  <option value="proposal">Proposal Sent</option>
                  <option value="negotiation">Negotiation</option>
                  <option value="won">Won</option>
                  <option value="lost">Lost</option>
                </select>
              </div>
            </div>
          </div>

          {/* Categorization */}
          <div>
            <h2 className="text-xl font-semibold mb-4" style={{ color: '#092C4C' }}>
              Categorization
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
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
                  disabled={saving}
                >
                  <option value="">Select a category</option>
                  <option value="product">Product</option>
                  <option value="service">Service</option>
                  <option value="consultation">Consultation</option>
                  <option value="other">Other</option>
                </select>
              </div>

              {formData.category === 'other' && (
                <div className="form-group">
                  <label htmlFor="category_other" className="label">
                    Other Category
                  </label>
                  <input
                    type="text"
                    id="category_other"
                    name="category_other"
                    value={formData.category_other}
                    onChange={handleChange}
                    className="input"
                    placeholder="Please specify"
                    disabled={saving}
                  />
                </div>
              )}

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
                  disabled={saving}
                >
                  <option value="">Select a source</option>
                  <option value="website">Website</option>
                  <option value="referral">Referral</option>
                  <option value="social_media">Social Media</option>
                  <option value="email">Email</option>
                  <option value="phone">Phone</option>
                  <option value="other">Other</option>
                </select>
              </div>

              {formData.source === 'other' && (
                <div className="form-group">
                  <label htmlFor="source_other" className="label">
                    Other Source
                  </label>
                  <input
                    type="text"
                    id="source_other"
                    name="source_other"
                    value={formData.source_other}
                    onChange={handleChange}
                    className="input"
                    placeholder="Please specify"
                    disabled={saving}
                  />
                </div>
              )}
            </div>
          </div>

          {/* Requirements & Budget */}
          <div>
            <h2 className="text-xl font-semibold mb-4" style={{ color: '#092C4C' }}>
              Requirements & Budget
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="form-group">
                <label htmlFor="budget" className="label">
                  Budget
                </label>
                <input
                  type="number"
                  id="budget"
                  name="budget"
                  value={formData.budget}
                  onChange={handleChange}
                  className="input"
                  placeholder="Enter budget amount"
                  step="0.01"
                  disabled={saving}
                />
              </div>

              <div className="form-group">
                <label htmlFor="timeline" className="label">
                  Timeline
                </label>
                <input
                  type="date"
                  id="timeline"
                  name="timeline"
                  value={formData.timeline}
                  onChange={handleChange}
                  className="input"
                  disabled={saving}
                />
              </div>

              <div className="form-group">
                <label htmlFor="follow_up_date" className="label">
                  Follow-up Date
                </label>
                <input
                  type="date"
                  id="follow_up_date"
                  name="follow_up_date"
                  value={formData.follow_up_date}
                  onChange={handleChange}
                  className="input"
                  disabled={saving}
                />
              </div>

              <div className="flex items-center gap-4">
                <label htmlFor="decision_maker" className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    id="decision_maker"
                    name="decision_maker"
                    checked={formData.decision_maker}
                    onChange={handleChange}
                    disabled={saving}
                    className="w-4 h-4"
                  />
                  <span className="text-gray-700">Is Decision Maker?</span>
                </label>
              </div>
            </div>
          </div>

          {/* Details */}
          <div>
            <h2 className="text-xl font-semibold mb-4" style={{ color: '#092C4C' }}>
              Details
            </h2>
            <div className="form-group">
              <label htmlFor="requirement" className="label">
                Requirements
              </label>
              <textarea
                id="requirement"
                name="requirement"
                value={formData.requirement}
                onChange={handleChange}
                className="input resize-none"
                rows={4}
                placeholder="Describe the lead's requirements"
                disabled={saving}
              />
            </div>

            <div className="form-group">
              <label htmlFor="notes" className="label">
                Notes
              </label>
              <textarea
                id="notes"
                name="notes"
                value={formData.notes}
                onChange={handleChange}
                className="input resize-none"
                rows={4}
                placeholder="Add any additional notes"
                disabled={saving}
              />
            </div>
          </div>

          {/* Buttons */}
          <div className="flex gap-4 pt-4">
            <button
              type="submit"
              disabled={saving}
              className="btn-primary px-8 py-3 font-semibold"
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
            <button
              type="button"
              onClick={() => navigate(`/leads/${id}`)}
              disabled={saving}
              className="btn-outline px-8 py-3 font-semibold"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
