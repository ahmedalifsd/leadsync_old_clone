import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Navbar } from '../components/Navbar';
import { api } from '../services/api';

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

export const AddLeadPage = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState<LeadFormData>({
    client_name: '',
    email: '',
    contact_number: '',
    category: '',
    category_other: '',
    source: '',
    source_other: '',
    requirement: '',
    status: 'new',
    budget: '',
    timeline: '',
    decision_maker: false,
    notes: '',
    follow_up_date: '',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  const handleChange = (
    e: React.ChangeEvent<
      HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
    >
  ) => {
    const { name, value, type } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]:
        type === 'checkbox' ? (e.target as HTMLInputElement).checked : value,
    }));
    if (errors[name]) {
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[name];
        return newErrors;
      });
    }
  };

  const validateForm = () => {
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
    const newErrors = validateForm();

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    setLoading(true);
    try {
      const submitData = {
        ...formData,
        budget: formData.budget ? parseFloat(formData.budget) : null,
      };

      await api.createLead(submitData);
      navigate('/leads');
    } catch (err) {
      console.error('Failed to create lead:', err);
      setErrors({
        submit: 'Failed to create lead. Please try again.',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold" style={{ color: '#092C4C' }}>
            Add New Lead
          </h1>
          <p className="text-gray-600 mt-2">Create a new lead record</p>
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
                  disabled={loading}
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
                  disabled={loading}
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
                  disabled={loading}
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
                  disabled={loading}
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
                  disabled={loading}
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
                    disabled={loading}
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
                  disabled={loading}
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
                    disabled={loading}
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
                  disabled={loading}
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
                  disabled={loading}
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
                  disabled={loading}
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
                    disabled={loading}
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
                disabled={loading}
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
                disabled={loading}
              />
            </div>
          </div>

          {/* Buttons */}
          <div className="flex gap-4 pt-4">
            <button
              type="submit"
              disabled={loading}
              className="btn-primary px-8 py-3 font-semibold"
            >
              {loading ? 'Creating Lead...' : 'Create Lead'}
            </button>
            <button
              type="button"
              onClick={() => navigate('/leads')}
              disabled={loading}
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
