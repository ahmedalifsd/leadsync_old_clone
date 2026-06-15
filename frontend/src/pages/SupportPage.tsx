import { useState } from 'react';
import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';

export const SupportPage = () => {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    subject: '',
    message: '',
  });
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 1000));
      setSubmitted(true);
      setFormData({ name: '', email: '', subject: '', message: '' });
      setTimeout(() => setSubmitted(false), 5000);
    } catch (error) {
      console.error('Failed to submit support request:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-white flex flex-col">
      <Navbar />

      <div className="flex-1">
        {/* Header */}
        <section
          className="py-16 text-center"
          style={{ backgroundColor: '#f9f7f4' }}
        >
          <div className="max-w-4xl mx-auto px-4">
            <h1 className="text-4xl font-bold mb-4" style={{ color: '#092C4C' }}>
              How Can We Help?
            </h1>
            <p className="text-xl text-gray-600">
              We're here to support you every step of the way
            </p>
          </div>
        </section>

        {/* Support Options */}
        <section className="py-16">
          <div className="max-w-6xl mx-auto px-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-16">
              {/* Email Support */}
              <div className="card p-8 text-center">
                <div
                  className="w-16 h-16 rounded-full mx-auto mb-4 flex items-center justify-center text-2xl"
                  style={{ backgroundColor: '#8b640d', color: 'white' }}
                >
                  ✉️
                </div>
                <h3 className="text-xl font-semibold mb-2">Email Support</h3>
                <p className="text-gray-600 mb-4">
                  Send us an email and we'll respond within 24 hours
                </p>
                <a
                  href="mailto:support@leadsync.com"
                  className="font-semibold"
                  style={{ color: '#8b640d' }}
                >
                  support@leadsync.com
                </a>
              </div>

              {/* Live Chat */}
              <div className="card p-8 text-center">
                <div
                  className="w-16 h-16 rounded-full mx-auto mb-4 flex items-center justify-center text-2xl"
                  style={{ backgroundColor: '#8b640d', color: 'white' }}
                >
                  💬
                </div>
                <h3 className="text-xl font-semibold mb-2">Live Chat</h3>
                <p className="text-gray-600 mb-4">
                  Chat with our support team during business hours
                </p>
                <button
                  className="font-semibold"
                  style={{ color: '#8b640d' }}
                  onClick={() => alert('Live chat coming soon!')}
                >
                  Start Chat
                </button>
              </div>

              {/* Documentation */}
              <div className="card p-8 text-center">
                <div
                  className="w-16 h-16 rounded-full mx-auto mb-4 flex items-center justify-center text-2xl"
                  style={{ backgroundColor: '#8b640d', color: 'white' }}
                >
                  📚
                </div>
                <h3 className="text-xl font-semibold mb-2">Documentation</h3>
                <p className="text-gray-600 mb-4">
                  Check out our comprehensive guides and tutorials
                </p>
                <a
                  href="#"
                  className="font-semibold"
                  style={{ color: '#8b640d' }}
                >
                  View Docs
                </a>
              </div>
            </div>

            {/* Support Form */}
            <div className="max-w-2xl mx-auto">
              <h2 className="text-3xl font-bold mb-8 text-center" style={{ color: '#092C4C' }}>
                Send us a Message
              </h2>

              {submitted && (
                <div className="bg-green-50 border border-green-200 text-green-700 px-6 py-4 rounded-lg mb-8">
                  Thank you for your message! We'll get back to you soon.
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="form-group">
                    <label htmlFor="name" className="label">
                      Your Name
                    </label>
                    <input
                      type="text"
                      id="name"
                      name="name"
                      value={formData.name}
                      onChange={handleChange}
                      className="input"
                      required
                      disabled={loading}
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="email" className="label">
                      Email Address
                    </label>
                    <input
                      type="email"
                      id="email"
                      name="email"
                      value={formData.email}
                      onChange={handleChange}
                      className="input"
                      required
                      disabled={loading}
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label htmlFor="subject" className="label">
                    Subject
                  </label>
                  <input
                    type="text"
                    id="subject"
                    name="subject"
                    value={formData.subject}
                    onChange={handleChange}
                    className="input"
                    placeholder="What is this about?"
                    required
                    disabled={loading}
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="message" className="label">
                    Message
                  </label>
                  <textarea
                    id="message"
                    name="message"
                    value={formData.message}
                    onChange={handleChange}
                    className="input resize-none"
                    rows={6}
                    placeholder="Tell us more about your issue..."
                    required
                    disabled={loading}
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="btn-primary w-full py-3 font-semibold"
                >
                  {loading ? 'Sending...' : 'Send Message'}
                </button>
              </form>
            </div>
          </div>
        </section>

        {/* FAQ */}
        <section className="bg-gray-50 py-16">
          <div className="max-w-4xl mx-auto px-4">
            <h2 className="text-3xl font-bold text-center mb-12" style={{ color: '#092C4C' }}>
              Frequently Asked Questions
            </h2>

            <div className="space-y-6">
              {[
                {
                  q: 'How do I reset my password?',
                  a: 'Click on "Forgot Password" on the login page and follow the instructions sent to your email.',
                },
                {
                  q: 'Can I export my leads?',
                  a: 'Yes, you can export your leads as CSV from the leads page. Click the export button in the toolbar.',
                },
                {
                  q: 'What happens to my data if I cancel my subscription?',
                  a: 'Your data will be retained for 30 days after cancellation. You can request a data export anytime.',
                },
                {
                  q: 'Is my data backed up?',
                  a: 'Yes, we automatically backup all data daily and store it securely.',
                },
                {
                  q: 'How do I add team members?',
                  a: 'Go to Team Settings and click "Invite Member". Enter their email address and select their role.',
                },
                {
                  q: 'What payment methods do you accept?',
                  a: 'We accept credit cards, PayPal, and bank transfers.',
                },
              ].map((faq, idx) => (
                <div key={idx} className="card p-6">
                  <h3 className="font-semibold mb-2" style={{ color: '#092C4C' }}>
                    {faq.q}
                  </h3>
                  <p className="text-gray-600">{faq.a}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>

      <Footer />
    </div>
  );
};
