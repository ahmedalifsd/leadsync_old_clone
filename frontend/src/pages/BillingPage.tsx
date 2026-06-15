import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import type { Subscription, BillingHistory } from '../types';

export const BillingPage = () => {
  const { user } = useAuth();
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [billingHistory, setBillingHistory] = useState<BillingHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadBillingData();
  }, []);

  const loadBillingData = async () => {
    try {
      setLoading(true);
      const [subResponse, historyResponse] = await Promise.all([
        api.getSubscription?.(),
        api.getBillingHistory?.()
      ]);
      
      if (subResponse?.data) setSubscription(subResponse.data);
      if (historyResponse?.data) setBillingHistory(historyResponse.data);
      setError(null);
    } catch (err) {
      setError('Failed to load billing information');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = (planId: string) => {
    // Redirect to Stripe checkout
    window.location.href = `/billing/checkout/${planId}`;
  };

  const handleCancel = async () => {
    if (window.confirm('Are you sure you want to cancel your subscription?')) {
      try {
        await api.cancelSubscription?.();
        setError(null);
        loadBillingData();
      } catch (err) {
        setError('Failed to cancel subscription');
        console.error(err);
      }
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Billing & Subscription</h1>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {loading ? (
          <div className="text-center py-12">
            <p className="text-gray-500">Loading billing information...</p>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
              {/* Current Plan */}
              <div className="lg:col-span-2">
                <div className="bg-white rounded-lg shadow-sm p-6">
                  <h2 className="text-2xl font-bold text-gray-900 mb-6">Current Plan</h2>
                  
                  {subscription ? (
                    <>
                      <div className="mb-6">
                        <p className="text-sm text-gray-600 mb-2">Plan Name</p>
                        <p className="text-2xl font-bold text-primary">{subscription.plan?.name}</p>
                      </div>

                      <div className="grid grid-cols-2 gap-6 mb-6">
                        <div>
                          <p className="text-sm text-gray-600 mb-2">Price</p>
                          <p className="text-2xl font-bold text-gray-900">
                            ${subscription.plan?.price}/month
                          </p>
                        </div>
                        <div>
                          <p className="text-sm text-gray-600 mb-2">Status</p>
                          <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                            subscription.status === 'active' 
                              ? 'bg-green-100 text-green-800' 
                              : 'bg-yellow-100 text-yellow-800'
                          }`}>
                            {subscription.status?.toUpperCase()}
                          </span>
                        </div>
                      </div>

                      {subscription.next_billing_date && (
                        <div className="mb-6 p-4 bg-blue-50 rounded-lg">
                          <p className="text-sm text-blue-600">
                            Next billing date: {new Date(subscription.next_billing_date).toLocaleDateString()}
                          </p>
                        </div>
                      )}

                      <div className="flex gap-3">
                        <button className="btn-primary flex-1">Upgrade Plan</button>
                        {subscription.status === 'active' && (
                          <button 
                            onClick={handleCancel}
                            className="btn-outline flex-1"
                          >
                            Cancel Subscription
                          </button>
                        )}
                      </div>
                    </>
                  ) : (
                    <div className="text-center py-8">
                      <p className="text-gray-600 mb-4">No active subscription</p>
                      <button className="btn-primary">Choose a Plan</button>
                    </div>
                  )}
                </div>
              </div>

              {/* Billing Summary */}
              <div className="bg-white rounded-lg shadow-sm p-6">
                <h3 className="text-lg font-bold text-gray-900 mb-4">Billing Summary</h3>
                <div className="space-y-4">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Subtotal</span>
                    <span className="text-gray-900 font-medium">${subscription?.plan?.price || 0}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Tax</span>
                    <span className="text-gray-900 font-medium">$0.00</span>
                  </div>
                  <div className="border-t pt-4 flex justify-between">
                    <span className="text-gray-900 font-bold">Total</span>
                    <span className="text-gray-900 font-bold">${subscription?.plan?.price || 0}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Billing History */}
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Billing History</h2>
              
              {billingHistory.length === 0 ? (
                <p className="text-center text-gray-500 py-8">No billing history</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50 border-b">
                      <tr>
                        <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Date</th>
                        <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Description</th>
                        <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Amount</th>
                        <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {billingHistory.map(invoice => (
                        <tr key={invoice.id} className="hover:bg-gray-50">
                          <td className="px-6 py-4 text-sm text-gray-600">
                            {new Date(invoice.date).toLocaleDateString()}
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-900">
                            {invoice.description}
                          </td>
                          <td className="px-6 py-4 text-sm font-medium text-gray-900">
                            ${invoice.amount.toFixed(2)}
                          </td>
                          <td className="px-6 py-4 text-sm">
                            <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${
                              invoice.status === 'paid'
                                ? 'bg-green-100 text-green-800'
                                : invoice.status === 'pending'
                                ? 'bg-yellow-100 text-yellow-800'
                                : 'bg-red-100 text-red-800'
                            }`}>
                              {invoice.status.toUpperCase()}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Payment Method */}
            <div className="mt-6 bg-white rounded-lg shadow-sm p-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Payment Method</h2>
              <p className="text-gray-600 mb-4">Manage your payment methods and billing preferences</p>
              <button className="btn-primary">Update Payment Method</button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
