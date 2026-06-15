import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import './index.css';

// Pages to be created
const App = () => {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public Routes */}
          {/* <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route path="/my-plans" element={<PlansPage />} />
          <Route path="/privacy-policy" element={<PrivacyPage />} />
          <Route path="/terms-and-conditions" element={<TermsPage />} />
          <Route path="/support" element={<SupportPage />} /> */}

          {/* Protected Routes */}
          {/* <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />

          {/* Leads Routes */}
          {/* <Route
            path="/leads"
            element={
              <ProtectedRoute>
                <LeadsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/leads/add"
            element={
              <ProtectedRoute>
                <AddLeadPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/leads/:id"
            element={
              <ProtectedRoute>
                <LeadDetailPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/leads/:id/edit"
            element={
              <ProtectedRoute>
                <EditLeadPage />
              </ProtectedRoute>
            }
          /> */}

          {/* Fallback */}
          <Route path="*" element={<div className="text-center py-12">Page not found</div>} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
};

export default App;
