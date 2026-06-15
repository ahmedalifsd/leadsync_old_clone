import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export const Navbar = () => {
  const [isOpen, setIsOpen] = useState(false);
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <nav className="bg-white shadow-sm sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <Link to={user ? '/dashboard' : '/'} className="flex-shrink-0">
            <div className="text-2xl font-bold" style={{ color: '#8b640d' }}>
              LeadSync
            </div>
          </Link>

          {/* Desktop Menu */}
          <div className="hidden md:flex items-center space-x-8">
            {!user ? (
              <>
                <Link
                  to="/my-plans"
                  className="text-gray-700 hover:text-primary font-medium"
                >
                  Plans
                </Link>
                <Link to="/login" className="btn-outline">
                  Login
                </Link>
                <Link to="/signup" className="btn-primary">
                  Get Started
                </Link>
              </>
            ) : (
              <>
                <Link
                  to="/dashboard"
                  className="text-gray-700 hover:text-primary font-medium"
                >
                  Dashboard
                </Link>
                <Link
                  to="/leads"
                  className="text-gray-700 hover:text-primary font-medium"
                >
                  Leads
                </Link>
                <Link
                  to="/templates"
                  className="text-gray-700 hover:text-primary font-medium"
                >
                  Templates
                </Link>
                <Link
                  to="/analytics"
                  className="text-gray-700 hover:text-primary font-medium"
                >
                  Analytics
                </Link>
                <Link
                  to="/activity"
                  className="text-gray-700 hover:text-primary font-medium"
                >
                  Activity
                </Link>
                <div className="flex items-center space-x-4 ml-4 pl-4 border-l">
                  <Link
                    to="/settings"
                    className="text-gray-700 hover:text-primary font-medium"
                  >
                    Settings
                  </Link>
                  <span className="text-gray-700 font-medium">{user.username}</span>
                  <button
                    onClick={handleLogout}
                    className="btn-outline text-sm"
                  >
                    Logout
                  </button>
                </div>
              </>
            )}
          </div>

          {/* Mobile Menu Button */}
          <button
            onClick={() => setIsOpen(!isOpen)}
            className="md:hidden inline-flex items-center justify-center p-2 rounded-md text-gray-700 hover:text-primary"
          >
            <svg
              className="h-6 w-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 6h16M4 12h16M4 18h16"
              />
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {isOpen && (
        <div className="md:hidden bg-white border-t">
          <div className="px-2 pt-2 pb-3 space-y-1">
            {!user ? (
              <>
                <Link
                  to="/my-plans"
                  className="block px-3 py-2 rounded-md text-gray-700 hover:bg-gray-100"
                >
                  Plans
                </Link>
                <Link
                  to="/login"
                  className="block px-3 py-2 rounded-md text-gray-700 hover:bg-gray-100"
                >
                  Login
                </Link>
                <Link
                  to="/signup"
                  className="block px-3 py-2 rounded-md text-white font-medium"
                  style={{ backgroundColor: '#8b640d' }}
                >
                  Get Started
                </Link>
              </>
            ) : (
              <>
                <Link
                  to="/dashboard"
                  className="block px-3 py-2 rounded-md text-gray-700 hover:bg-gray-100"
                >
                  Dashboard
                </Link>
                <Link
                  to="/leads"
                  className="block px-3 py-2 rounded-md text-gray-700 hover:bg-gray-100"
                >
                  Leads
                </Link>
                <Link
                  to="/templates"
                  className="block px-3 py-2 rounded-md text-gray-700 hover:bg-gray-100"
                >
                  Templates
                </Link>
                <Link
                  to="/analytics"
                  className="block px-3 py-2 rounded-md text-gray-700 hover:bg-gray-100"
                >
                  Analytics
                </Link>
                <Link
                  to="/activity"
                  className="block px-3 py-2 rounded-md text-gray-700 hover:bg-gray-100"
                >
                  Activity
                </Link>
                <Link
                  to="/settings"
                  className="block px-3 py-2 rounded-md text-gray-700 hover:bg-gray-100"
                >
                  Settings
                </Link>
                <button
                  onClick={handleLogout}
                  className="block w-full text-left px-3 py-2 rounded-md text-gray-700 hover:bg-gray-100"
                >
                  Logout
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </nav>
  );
};
