import { Link } from 'react-router-dom';

export const Footer = () => {
  return (
    <footer className="bg-white border-t mt-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
          {/* Brand */}
          <div>
            <div className="text-2xl font-bold mb-4" style={{ color: '#8b640d' }}>
              LeadSync
            </div>
            <p className="text-gray-600 text-sm">
              Modern lead management system for your business
            </p>
          </div>

          {/* Product */}
          <div>
            <h3 className="font-semibold mb-4 text-gray-900">Product</h3>
            <ul className="space-y-2 text-sm">
              <li>
                <Link to="/my-plans" className="text-gray-600 hover:text-primary">
                  Plans & Pricing
                </Link>
              </li>
              <li>
                <Link to="/support" className="text-gray-600 hover:text-primary">
                  Support
                </Link>
              </li>
              <li>
                <a href="#" className="text-gray-600 hover:text-primary">
                  Features
                </a>
              </li>
            </ul>
          </div>

          {/* Legal */}
          <div>
            <h3 className="font-semibold mb-4 text-gray-900">Legal</h3>
            <ul className="space-y-2 text-sm">
              <li>
                <Link to="/privacy-policy" className="text-gray-600 hover:text-primary">
                  Privacy Policy
                </Link>
              </li>
              <li>
                <Link
                  to="/terms-and-conditions"
                  className="text-gray-600 hover:text-primary"
                >
                  Terms & Conditions
                </Link>
              </li>
            </ul>
          </div>

          {/* Connect */}
          <div>
            <h3 className="font-semibold mb-4 text-gray-900">Connect</h3>
            <ul className="space-y-2 text-sm">
              <li>
                <a href="#" className="text-gray-600 hover:text-primary">
                  Twitter
                </a>
              </li>
              <li>
                <a href="#" className="text-gray-600 hover:text-primary">
                  LinkedIn
                </a>
              </li>
              <li>
                <a href="#" className="text-gray-600 hover:text-primary">
                  Email
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="border-t pt-8">
          <p className="text-center text-gray-600 text-sm">
            © {new Date().getFullYear()} LeadSync. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
};
