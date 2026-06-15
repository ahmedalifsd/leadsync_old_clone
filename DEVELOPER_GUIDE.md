# Developer Guide - LeadSync CRM React Conversion

## Quick Start for Development

### Prerequisites
- Node.js 16+ and npm/yarn
- Python 3.8+ and pip
- PostgreSQL database

### Backend Setup (5 minutes)

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file (copy from .env.example)
cp .env.example .env
# Edit .env with your database credentials

# Run migrations
python manage.py migrate

# Start server
python manage.py runserver 0.0.0.0:8000
```

Backend will be available at: **http://localhost:8000**
API endpoints: **http://localhost:8000/api/**

### Frontend Setup (5 minutes)

```bash
cd frontend

# Install dependencies
npm install

# Create .env file (copy from .env.example)
cp .env.example .env
# Update VITE_API_URL if backend is on different port

# Start dev server with HMR
npm run dev
```

Frontend will be available at: **http://localhost:5173**

---

## Project Structure Guide

### Backend Structure

```
backend/
├── LeadSync/          # Django project settings
│   ├── settings.py    # Main settings (API configured)
│   ├── urls.py        # API routes at /api/
│   └── wsgi.py
│
├── core/              # Lead management app
│   ├── models.py      # Lead, Category, Source models
│   ├── views.py       # Original Django views (keep for compatibility)
│   ├── serializers.py # DRF serializers (NEW)
│   ├── api_views.py   # REST API views (NEW)
│   ├── api_urls.py    # API routing (NEW)
│   └── urls.py        # Original URL routing
│
├── accounts/          # User authentication
│   ├── models.py      # User, UserProfile models
│   ├── views.py       # Original auth views
│   ├── serializers.py # DRF serializers (NEW)
│   ├── api_views.py   # Auth API endpoints (NEW)
│   └── api_urls.py    # Auth routing (NEW)
│
├── billing/           # Payments and plans
│   ├── models.py
│   └── views.py
│
├── team/              # Team management
│   ├── models.py
│   └── views.py
│
├── static/            # Static files
├── templates/         # Django templates (keep for old routes)
├── manage.py
├── requirements.txt   # Python dependencies
└── .env.example       # Environment template
```

### Frontend Structure

```
frontend/src/
├── services/
│   ├── api.ts         # API client - 200+ lines
│   │   └── Methods for all 50+ endpoints
│   ├── db.ts          # IndexedDB wrapper - 280+ lines
│   │   └── CRUD operations + sync queue
│   └── sync.ts        # Offline sync logic - 200+ lines
│       └── Queue processing, retry, conflict resolution
│
├── context/
│   └── AuthContext.tsx # Auth state management
│       └── Login, logout, register, profile update
│
├── components/        # React components (to be created)
│   ├── ProtectedRoute.tsx
│   ├── Layout/
│   │   ├── Navbar.tsx
│   │   ├── Sidebar.tsx
│   │   └── Footer.tsx
│   ├── Auth/
│   │   ├── LoginForm.tsx
│   │   └── SignupForm.tsx
│   ├── Dashboard/
│   │   └── ...
│   └── Leads/
│       ├── LeadList.tsx
│       ├── LeadForm.tsx
│       └── ...
│
├── pages/             # Page components (to be created)
│   ├── HomePage.tsx
│   ├── LoginPage.tsx
│   ├── DashboardPage.tsx
│   ├── LeadsPage.tsx
│   └── ...
│
├── types/
│   └── index.ts       # TypeScript types - 190+ lines
│       ├── Lead, Category, Source
│       ├── User, UserProfile
│       ├── LeadStatus enums & colors
│       └── Form & API response types
│
├── hooks/             # Custom hooks (to be created)
│   ├── useLeads.ts
│   ├── useCategories.ts
│   ├── useOfflineSync.ts
│   └── ...
│
├── utils/             # Utility functions (to be created)
│   ├── formatters.ts
│   ├── validators.ts
│   └── helpers.ts
│
├── styles/
│   └── (Tailwind CSS only, no separate files needed)
│
├── App.tsx            # Main app component with routing
├── index.css          # Global styles + Tailwind
├── main.tsx           # Entry point
├── tailwind.config.js # Tailwind configuration
└── postcss.config.js  # PostCSS setup
```

---

## API Usage Examples

### In Components/Pages

```typescript
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';

function MyComponent() {
  const { user } = useAuth();

  // Fetch leads
  const handleFetchLeads = async () => {
    try {
      const response = await api.getLeads(1, { status: 'interested' });
      console.log(response.data.results); // Array of leads
    } catch (error) {
      console.error('Failed to fetch leads:', error);
    }
  };

  // Create lead
  const handleCreateLead = async () => {
    try {
      const response = await api.createLead({
        client_name: 'John Doe',
        email: 'john@example.com',
        status: 'new',
        category: 1,
        source: 1,
      });
      console.log('Lead created:', response.data);
    } catch (error) {
      console.error('Failed to create lead:', error);
    }
  };

  return (
    <div>
      <button onClick={handleFetchLeads}>Fetch Leads</button>
      <button onClick={handleCreateLead}>Create Lead</button>
    </div>
  );
}
```

### Using Database Service (Offline)

```typescript
import { db } from '../services/db';

// Get cached leads
const leads = await db.getLeads();

// Add lead (goes to sync queue)
const id = await db.addLead({
  client_name: 'Jane Doe',
  email: 'jane@example.com',
  status: 'new',
});

// Update lead
await db.updateLead(id, { status: 'contacted' });

// Delete lead
await db.deleteLead(id);
```

### Using Sync Service

```typescript
import { syncService } from '../services/sync';

// Initialize sync on app startup
syncService.initialize();

// Listen for sync status changes
const unsubscribe = syncService.onSyncStatusChange((status) => {
  console.log('Sync status:', status); // 'online', 'offline', 'syncing', 'synced'
});

// Manually trigger sync
await syncService.syncPendingChanges();

// Check status
console.log(syncService.isOnline());
console.log(syncService.isSyncing());
```

---

## Building Pages - Step by Step

### 1. Create Page Component

```typescript
// pages/LeadsPage.tsx
import { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { Lead, PaginatedResponse } from '../types';

export function LeadsPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchLeads();
  }, []);

  const fetchLeads = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.getLeads(1);
      setLeads(response.data.results);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div>
      <h1>Leads</h1>
      <ul>
        {leads.map(lead => (
          <li key={lead.id}>{lead.client_name}</li>
        ))}
      </ul>
    </div>
  );
}
```

### 2. Add Route to App.tsx

```typescript
import { LeadsPage } from './pages/LeadsPage';

<Route
  path="/leads"
  element={
    <ProtectedRoute>
      <LeadsPage />
    </ProtectedRoute>
  }
/>
```

### 3. Style with Tailwind

Use Tailwind classes and custom components from `index.css`:

```typescript
<div className="card p-6">
  <h2 className="text-2xl font-display font-bold mb-4">Leads</h2>
  <table className="w-full">
    {/* ... */}
  </table>
</div>
```

---

## Available Tailwind Classes

### Custom Components
```
.btn           - Base button style
.btn-primary   - Primary color button
.btn-secondary - Secondary color button
.btn-accent    - Accent color button
.btn-outline   - Outlined button
.btn-small     - Smaller button
.btn-large     - Larger button

.badge         - Base badge
.badge-primary - Primary badge
.badge-success - Success badge
.badge-error   - Error badge

.card          - Card container
.card-bordered - Card with border

.input         - Input field
.input-error   - Error state input
.label         - Form label
.form-group    - Form field wrapper

.text-primary  - Primary text color
.text-error    - Error text color
.text-muted    - Muted text color

.section       - Padded section
.container-main - Max width container
.empty-state   - Empty state container
```

### Colors Available
```
primary, primary-light, primary-dark
secondary, secondary-light
accent, accent-light, accent-dark
success, warning, error
neutral, neutral-dark
```

---

## Type Safety

All types are defined in `src/types/index.ts`. Use them in your components:

```typescript
import type { Lead, LeadStatus, LeadFilters, DashboardStats } from '../types';

// Lead status
const status: LeadStatus = 'interested';

// Filter leads
const filters: LeadFilters = {
  status: 'qualified',
  category: 1,
  page: 1,
};

// Safe enum access
const label = LEAD_STATUS_LABELS['won']; // 'Won'
const color = LEAD_STATUS_COLORS['new']; // 'bg-blue-100 text-blue-800'
```

---

## Authentication Flow

```
1. User visits /login
2. LoginPage component displays form
3. Form submits to api.login(username, password)
4. api.login() makes POST /api/auth/login/
5. Backend returns user data
6. AuthContext stores user in state + localStorage
7. ProtectedRoute components can now access user
8. app.tsx redirects to /dashboard
```

---

## Offline-First Flow

```
ONLINE:
1. User creates lead in UI
2. api.createLead() sends to server
3. Lead added to database
4. UI updates
5. No local queue entry

OFFLINE:
1. User creates lead in UI
2. db.addLead() called
3. Lead added to IndexedDB
4. syncQueue entry created (pending)
5. UI shows "syncing" status

CONNECTION RESTORED:
1. Online event detected
2. syncService.syncPendingChanges() called
3. Each queue item processed
4. API called for each change
5. Local lead ID replaced with server ID
6. UI shows "synced" status
```

---

## Environment Variables

### Backend (.env)

```env
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://user:password@localhost:5432/leadsync
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

### Frontend (.env)

```env
VITE_API_URL=http://localhost:8000/api
VITE_APP_NAME=LeadSync CRM
```

---

## Common Tasks

### Add New API Endpoint

1. Create view in `core/api_views.py` (or auth app)
2. Create serializer in `core/serializers.py`
3. Register in router in `core/api_urls.py`
4. Add method to api client in `frontend/services/api.ts`
5. Use in component via `api.methodName()`

### Add New Page

1. Create component in `frontend/src/pages/`
2. Create route in `App.tsx`
3. Wrap with `<ProtectedRoute>` if auth required
4. Create components in `frontend/src/components/` as needed
5. Import types from `frontend/src/types/index.ts`

### Add Form Validation

1. Create validator function in `frontend/src/utils/validators.ts`
2. Call validator in form submission handler
3. Show errors in input elements
4. Use `.input-error` class for error state

### Test Offline

1. Open DevTools (F12)
2. Go to Network tab
3. Check "Offline" checkbox
4. Make changes in app
5. Uncheck offline
6. Changes should sync automatically

---

## Debugging Tips

### API Issues
```typescript
// Add logging in api.ts interceptor
this.client.interceptors.response.use(
  response => {
    console.log('[v0] API Response:', response);
    return response;
  },
  error => {
    console.error('[v0] API Error:', error);
    return Promise.reject(error);
  }
);
```

### Offline Issues
```typescript
// Check sync queue
const queue = await db.getPendingSyncItems();
console.log('[v0] Sync Queue:', queue);

// Check local data
const leads = await db.getLeads();
console.log('[v0] Cached Leads:', leads);
```

### Auth Issues
```typescript
// Check stored user
const user = JSON.parse(localStorage.getItem('user') || '{}');
console.log('[v0] Stored User:', user);

// Check current auth context
const { user, isAuthenticated } = useAuth();
console.log('[v0] Auth State:', { user, isAuthenticated });
```

---

## Performance Optimization

1. **Code splitting**: Routes are automatically code-split by Vite
2. **Image optimization**: Use Vite's image import
3. **Memoization**: Use React.memo for expensive components
4. **Pagination**: Always paginate large lists (default 50 per page)
5. **Caching**: React Query caches API responses automatically
6. **IndexedDB**: Uses indexing for fast queries

---

## Next Phase Checklist

- [ ] Build Phase 3 public pages (Home, Login, Signup, Plans)
- [ ] Create Layout component with Navbar & Footer
- [ ] Implement form validation
- [ ] Test authentication flow
- [ ] Verify API connectivity
- [ ] Style pages to match original design
- [ ] Deploy to production

---

## Common Errors & Solutions

### CORS Error
```
Error: Access to XMLHttpRequest blocked by CORS
Solution: Check CORS_ALLOWED_ORIGINS in backend/LeadSync/settings.py
Add your frontend URL to the list
```

### 401 Unauthorized
```
Error: {"detail":"Unauthorized"}
Solution: User not logged in, redirect to /login
AuthContext handles this automatically via interceptor
```

### IndexedDB Full
```
Error: QuotaExceededError
Solution: User's browser storage is full
Clear old data or ask user to free space
```

### Service Worker Not Found
```
Error: Failed to load service worker
Solution: Service worker setup not yet implemented
Will be added in Phase 7
```

---

This guide covers everything needed to continue development. Start with Phase 3!
