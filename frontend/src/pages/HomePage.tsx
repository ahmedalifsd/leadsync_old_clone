import { Link } from 'react-router-dom';
import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';

export const HomePage = () => {
  return (
    <div className="min-h-screen bg-white">
      <Navbar />

      {/* Hero Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="text-center">
          <h1 className="text-5xl md:text-6xl font-bold mb-6" style={{ color: '#092C4C' }}>
            Manage Your Leads Efficiently
          </h1>
          <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
            LeadSync is a modern lead management system designed to help you organize, track, and convert leads into customers with ease.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link to="/signup" className="btn-primary btn-large">
              Get Started Free
            </Link>
            <Link to="/my-plans" className="btn-outline btn-large">
              View Plans
            </Link>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="bg-gray-50 py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-center mb-12" style={{ color: '#092C4C' }}>
            Why Choose LeadSync?
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {/* Feature 1 */}
            <div className="card p-6">
              <div
                className="w-12 h-12 rounded-lg mb-4 flex items-center justify-center text-white text-xl"
                style={{ backgroundColor: '#8b640d' }}
              >
                📊
              </div>
              <h3 className="text-xl font-semibold mb-3">Real-time Analytics</h3>
              <p className="text-gray-600">
                Get instant insights into your lead pipeline with comprehensive dashboards and reports
              </p>
            </div>

            {/* Feature 2 */}
            <div className="card p-6">
              <div
                className="w-12 h-12 rounded-lg mb-4 flex items-center justify-center text-white text-xl"
                style={{ backgroundColor: '#8b640d' }}
              >
                🔄
              </div>
              <h3 className="text-xl font-semibold mb-3">Works Offline</h3>
              <p className="text-gray-600">
                Continue working even without internet. All changes sync automatically when you're back online
              </p>
            </div>

            {/* Feature 3 */}
            <div className="card p-6">
              <div
                className="w-12 h-12 rounded-lg mb-4 flex items-center justify-center text-white text-xl"
                style={{ backgroundColor: '#8b640d' }}
              >
                👥
              </div>
              <h3 className="text-xl font-semibold mb-3">Team Collaboration</h3>
              <p className="text-gray-600">
                Collaborate seamlessly with your team with real-time notifications and activity logs
              </p>
            </div>

            {/* Feature 4 */}
            <div className="card p-6">
              <div
                className="w-12 h-12 rounded-lg mb-4 flex items-center justify-center text-white text-xl"
                style={{ backgroundColor: '#8b640d' }}
              >
                🛡️
              </div>
              <h3 className="text-xl font-semibold mb-3">Secure & Reliable</h3>
              <p className="text-gray-600">
                Your data is encrypted and backed up. We take security seriously
              </p>
            </div>

            {/* Feature 5 */}
            <div className="card p-6">
              <div
                className="w-12 h-12 rounded-lg mb-4 flex items-center justify-center text-white text-xl"
                style={{ backgroundColor: '#8b640d' }}
              >
                ⚡
              </div>
              <h3 className="text-xl font-semibold mb-3">Fast & Responsive</h3>
              <p className="text-gray-600">
                Lightning-fast performance with a responsive interface that works on all devices
              </p>
            </div>

            {/* Feature 6 */}
            <div className="card p-6">
              <div
                className="w-12 h-12 rounded-lg mb-4 flex items-center justify-center text-white text-xl"
                style={{ backgroundColor: '#8b640d' }}
              >
                🎯
              </div>
              <h3 className="text-xl font-semibold mb-3">Lead Scoring</h3>
              <p className="text-gray-600">
                Automatically score and prioritize your leads based on engagement and custom criteria
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold mb-6" style={{ color: '#092C4C' }}>
            Ready to Get Started?
          </h2>
          <p className="text-xl text-gray-600 mb-8">
            Join hundreds of businesses using LeadSync to manage their leads more effectively
          </p>
          <Link to="/signup" className="btn-primary btn-large inline-block">
            Create Your Free Account
          </Link>
        </div>
      </section>

      <Footer />
    </div>
  );
};
