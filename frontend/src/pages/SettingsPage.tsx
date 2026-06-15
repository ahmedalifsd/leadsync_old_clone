import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Navbar } from '../components/Navbar';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';

export const SettingsPage = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('profile');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  const [profileData, setProfileData] = useState({
    first_name: user?.first_name || '',
    last_name: user?.last_name || '',
    email: user?.email || '',
  });

  const [passwordData, setPasswordData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  });

  const [preferences, setPreferences] = useState({
    email_notifications: true,
    activity_notifications: true,
    marketing_emails: false,
    items_per_page: '20',
    theme: 'light',
  });

  const handleProfileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setProfileData((prev) => ({ ...prev, [name]: value }));
  };

  const handlePasswordChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setPasswordData((prev) => ({ ...prev, [name]: value }));
  };

  const handlePreferenceChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    setPreferences((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : value,
    }));
  };

  const handleProfileSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      await api.updateProfile(profileData);
      setSuccess('Profile updated successfully');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError('Failed to update profile');
      console.error('Profile update error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (passwordData.new_password !== passwordData.confirm_password) {
      setError('New passwords do not match');
      return;
    }

    if (passwordData.new_password.length < 8) {
      setError('New password must be at least 8 characters');
      return;
    }

    setLoading(true);
    setError('');
    setSuccess('');

    try {
      await api.changePassword({
        current_password: passwordData.current_password,
        new_password: passwordData.new_password,
      });
      setSuccess('Password changed successfully');
      setPasswordData({
        current_password: '',
        new_password: '',
        confirm_password: '',
      });
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError('Failed to change password. Check your current password.');
      console.error('Password change error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    if (!window.confirm('Are you sure you want to log out?')) return;

    try {
      await logout();
      navigate('/login');
    } catch (err) {
      setError('Failed to logout');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold" style={{ color: '#092C4C' }}>
            Settings
          </h1>
          <p className="text-gray-600 mt-2">Manage your account and preferences</p>
        </div>

        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
            {error}
          </div>
        )}

        {success && (
          <div className="mb-6 bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg">
            {success}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Sidebar Navigation */}
          <div className="md:col-span-1">
            <nav className="space-y-1">
              {[
                { id: 'profile', label: 'Profile' },
                { id: 'password', label: 'Password' },
                { id: 'preferences', label: 'Preferences' },
                { id: 'danger', label: 'Danger Zone' },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full text-left px-4 py-2 rounded-lg font-medium transition-colors ${
                    activeTab === tab.id
                      ? 'bg-primary text-white'
                      : 'text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          {/* Content */}
          <div className="md:col-span-3">
            {/* Profile Tab */}
            {activeTab === 'profile' && (
              <div className="card p-6">
                <h2 className="text-xl font-semibold mb-6" style={{ color: '#092C4C' }}>
                  Profile Information
                </h2>
                <form onSubmit={handleProfileSubmit} className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="form-group">
                      <label htmlFor="first_name" className="label">
                        First Name
                      </label>
                      <input
                        type="text"
                        id="first_name"
                        name="first_name"
                        value={profileData.first_name}
                        onChange={handleProfileChange}
                        className="input"
                        disabled={loading}
                      />
                    </div>

                    <div className="form-group">
                      <label htmlFor="last_name" className="label">
                        Last Name
                      </label>
                      <input
                        type="text"
                        id="last_name"
                        name="last_name"
                        value={profileData.last_name}
                        onChange={handleProfileChange}
                        className="input"
                        disabled={loading}
                      />
                    </div>
                  </div>

                  <div className="form-group">
                    <label htmlFor="email" className="label">
                      Email (Cannot be changed)
                    </label>
                    <input
                      type="email"
                      id="email"
                      name="email"
                      value={profileData.email}
                      disabled
                      className="input bg-gray-50"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Contact support to change your email
                    </p>
                  </div>

                  <div className="pt-4">
                    <button
                      type="submit"
                      disabled={loading}
                      className="btn-primary"
                    >
                      {loading ? 'Saving...' : 'Save Changes'}
                    </button>
                  </div>
                </form>
              </div>
            )}

            {/* Password Tab */}
            {activeTab === 'password' && (
              <div className="card p-6">
                <h2 className="text-xl font-semibold mb-6" style={{ color: '#092C4C' }}>
                  Change Password
                </h2>
                <form onSubmit={handlePasswordSubmit} className="space-y-4 max-w-md">
                  <div className="form-group">
                    <label htmlFor="current_password" className="label">
                      Current Password
                    </label>
                    <input
                      type="password"
                      id="current_password"
                      name="current_password"
                      value={passwordData.current_password}
                      onChange={handlePasswordChange}
                      className="input"
                      disabled={loading}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="new_password" className="label">
                      New Password
                    </label>
                    <input
                      type="password"
                      id="new_password"
                      name="new_password"
                      value={passwordData.new_password}
                      onChange={handlePasswordChange}
                      className="input"
                      disabled={loading}
                      required
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Minimum 8 characters
                    </p>
                  </div>

                  <div className="form-group">
                    <label htmlFor="confirm_password" className="label">
                      Confirm New Password
                    </label>
                    <input
                      type="password"
                      id="confirm_password"
                      name="confirm_password"
                      value={passwordData.confirm_password}
                      onChange={handlePasswordChange}
                      className="input"
                      disabled={loading}
                      required
                    />
                  </div>

                  <div className="pt-4">
                    <button
                      type="submit"
                      disabled={loading}
                      className="btn-primary"
                    >
                      {loading ? 'Changing...' : 'Change Password'}
                    </button>
                  </div>
                </form>
              </div>
            )}

            {/* Preferences Tab */}
            {activeTab === 'preferences' && (
              <div className="card p-6">
                <h2 className="text-xl font-semibold mb-6" style={{ color: '#092C4C' }}>
                  Preferences
                </h2>
                <form className="space-y-4">
                  <div>
                    <h3 className="font-semibold text-gray-900 mb-3">Notifications</h3>
                    <div className="space-y-2">
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          name="email_notifications"
                          checked={preferences.email_notifications}
                          onChange={handlePreferenceChange}
                          className="w-4 h-4"
                        />
                        <span className="text-gray-700">Email notifications</span>
                      </label>
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          name="activity_notifications"
                          checked={preferences.activity_notifications}
                          onChange={handlePreferenceChange}
                          className="w-4 h-4"
                        />
                        <span className="text-gray-700">Activity notifications</span>
                      </label>
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          name="marketing_emails"
                          checked={preferences.marketing_emails}
                          onChange={handlePreferenceChange}
                          className="w-4 h-4"
                        />
                        <span className="text-gray-700">Marketing emails</span>
                      </label>
                    </div>
                  </div>

                  <div className="border-t pt-4">
                    <h3 className="font-semibold text-gray-900 mb-3">Display</h3>
                    <div className="grid grid-cols-1 gap-4">
                      <div className="form-group">
                        <label htmlFor="items_per_page" className="label">
                          Items Per Page
                        </label>
                        <select
                          id="items_per_page"
                          name="items_per_page"
                          value={preferences.items_per_page}
                          onChange={handlePreferenceChange}
                          className="input"
                        >
                          <option value="10">10 items</option>
                          <option value="20">20 items</option>
                          <option value="50">50 items</option>
                          <option value="100">100 items</option>
                        </select>
                      </div>

                      <div className="form-group">
                        <label htmlFor="theme" className="label">
                          Theme
                        </label>
                        <select
                          id="theme"
                          name="theme"
                          value={preferences.theme}
                          onChange={handlePreferenceChange}
                          className="input"
                        >
                          <option value="light">Light</option>
                          <option value="dark">Dark (Coming Soon)</option>
                          <option value="auto">Auto</option>
                        </select>
                      </div>
                    </div>
                  </div>

                  <div className="pt-4">
                    <button type="button" className="btn-primary" disabled>
                      Preferences are auto-saved
                    </button>
                  </div>
                </form>
              </div>
            )}

            {/* Danger Zone Tab */}
            {activeTab === 'danger' && (
              <div className="card p-6 border-2 border-red-200">
                <h2 className="text-xl font-semibold mb-6 text-red-600">
                  Danger Zone
                </h2>

                <div className="space-y-4">
                  <div className="bg-red-50 border border-red-200 p-4 rounded-lg">
                    <h3 className="font-semibold text-red-900 mb-2">Logout</h3>
                    <p className="text-sm text-red-700 mb-3">
                      Sign out of your account
                    </p>
                    <button
                      onClick={handleLogout}
                      className="btn-outline text-red-600 border-red-200 hover:bg-red-50"
                    >
                      Logout Now
                    </button>
                  </div>

                  <div className="bg-red-50 border border-red-200 p-4 rounded-lg">
                    <h3 className="font-semibold text-red-900 mb-2">
                      Delete Account
                    </h3>
                    <p className="text-sm text-red-700 mb-3">
                      Permanently delete your account and all associated data.
                      This action cannot be undone.
                    </p>
                    <button
                      disabled
                      className="btn-outline text-red-600 border-red-200 opacity-50 cursor-not-allowed"
                    >
                      Delete Account (Coming Soon)
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
