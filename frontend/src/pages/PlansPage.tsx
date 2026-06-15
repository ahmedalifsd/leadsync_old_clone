import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';
import type { Plan } from '../types';

export const PlansPage = () => {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [billingPeriod, setBillingPeriod] = useState<'monthly' | 'yearly'>('monthly');

  useEffect(() => {
    const fetchPlans = async () => {
      try {
        const response = await api.getPlans();
        setPlans(response);
      } catch (error) {
        console.error('Failed to fetch plans:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchPlans();
  }, []);

  const getPrice = (plan: Plan) => {
    if (billingPeriod === 'yearly') {
      return plan.yearly_price;
    }
    return plan.monthly_price;
  };

  const getBillingLabel = () => {
    return billingPeriod === 'yearly' ? '/year' : '/month';
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading plans...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white flex flex-col">
      <Navbar />

      <div className="flex-1">
        {/* Pricing Header */}
        <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <div className="text-center mb-12">
            <h1 className="text-4xl font-bold mb-4" style={{ color: '#092C4C' }}>
              Simple, Transparent Pricing
            </h1>
            <p className="text-xl text-gray-600 mb-8">
              Choose the perfect plan for your business
            </p>

            {/* Billing Toggle */}
            <div className="flex justify-center items-center gap-4 mb-8">
              <button
                onClick={() => setBillingPeriod('monthly')}
                className={`px-6 py-2 rounded-lg font-medium transition-colors ${
                  billingPeriod === 'monthly'
                    ? 'text-white'
                    : 'text-gray-700 hover:text-primary'
                }`}
                style={{
                  backgroundColor:
                    billingPeriod === 'monthly' ? '#8b640d' : 'transparent',
                }}
              >
                Monthly
              </button>
              <button
                onClick={() => setBillingPeriod('yearly')}
                className={`px-6 py-2 rounded-lg font-medium transition-colors ${
                  billingPeriod === 'yearly'
                    ? 'text-white'
                    : 'text-gray-700 hover:text-primary'
                }`}
                style={{
                  backgroundColor:
                    billingPeriod === 'yearly' ? '#8b640d' : 'transparent',
                }}
              >
                Yearly
                <span
                  className="ml-2 inline-block text-xs font-semibold text-white px-2 py-1 rounded"
                  style={{ backgroundColor: '#F39C12' }}
                >
                  Save 20%
                </span>
              </button>
            </div>
          </div>

          {/* Plans Grid */}
          {plans.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-600">No plans available at the moment.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {plans.map((plan) => (
                <div
                  key={plan.id}
                  className="card border-2 hover:shadow-lg transition-all duration-300 overflow-hidden"
                  style={{
                    borderColor: '#8b640d',
                    ...(plan.is_default_signup_plan && {
                      transform: 'scale(1.05)',
                      boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
                    }),
                  }}
                >
                  {plan.is_default_signup_plan && (
                    <div
                      className="px-4 py-2 text-center text-white text-sm font-semibold"
                      style={{ backgroundColor: '#F39C12' }}
                    >
                      RECOMMENDED
                    </div>
                  )}

                  <div className="p-8">
                    <h3 className="text-2xl font-bold mb-2">{plan.name}</h3>

                    <div className="mb-6">
                      <div className="text-4xl font-bold" style={{ color: '#8b640d' }}>
                        {getPrice(plan)}
                      </div>
                      <div className="text-gray-600">{getBillingLabel()}</div>
                      {billingPeriod === 'yearly' && plan.yearly_savings && (
                        <div className="text-success text-sm mt-2">
                          Save {plan.yearly_savings} per year
                        </div>
                      )}
                    </div>

                    <Link
                      to="/signup"
                      className="btn-primary w-full py-3 font-semibold text-center block mb-6"
                    >
                      Get Started
                    </Link>

                    <div className="space-y-3 border-t pt-6">
                      <div className="flex items-start gap-3">
                        <span style={{ color: '#8b640d' }}>✓</span>
                        <span className="text-gray-700">
                          Up to {plan.max_employees} team member{plan.max_employees > 1 ? 's' : ''}
                        </span>
                      </div>

                      {plan.monthly_max_leads ? (
                        <div className="flex items-start gap-3">
                          <span style={{ color: '#8b640d' }}>✓</span>
                          <span className="text-gray-700">
                            {plan.monthly_max_leads} leads per month
                          </span>
                        </div>
                      ) : (
                        <div className="flex items-start gap-3">
                          <span style={{ color: '#8b640d' }}>✓</span>
                          <span className="text-gray-700">Unlimited leads</span>
                        </div>
                      )}

                      {plan.features &&
                        plan.features.split('\n').map((feature, idx) => (
                          feature.trim() && (
                            <div key={idx} className="flex items-start gap-3">
                              <span style={{ color: '#8b640d' }}>✓</span>
                              <span className="text-gray-700">{feature.trim()}</span>
                            </div>
                          )
                        ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* FAQ Section */}
        <section className="bg-gray-50 py-16">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2 className="text-3xl font-bold text-center mb-12" style={{ color: '#092C4C' }}>
              Frequently Asked Questions
            </h2>

            <div className="space-y-6">
              {[
                {
                  q: 'Can I change my plan later?',
                  a: 'Yes, you can upgrade or downgrade your plan anytime. Changes take effect immediately.',
                },
                {
                  q: 'Is there a free trial?',
                  a: 'Yes, all plans come with a 14-day free trial. No credit card required.',
                },
                {
                  q: 'Do you offer refunds?',
                  a: 'We offer a 30-day money-back guarantee if you&apos;re not satisfied.',
                },
                {
                  q: 'What payment methods do you accept?',
                  a: 'We accept all major credit cards, PayPal, and bank transfers.',
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
