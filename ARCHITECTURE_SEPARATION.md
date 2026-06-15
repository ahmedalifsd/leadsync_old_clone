# LeadSync CRM: Backend & Frontend Separation

## Overview

This project implements **complete separation** between backend and frontend:

- **Backend**: Pure REST API (Django) - NO UI/templates
- **Frontend**: Pure React app - NO backend server required

This is the correct microservices architecture where each component is independently deployable.

---

## Backend Architecture (API-Only)

### What Backend Does
- Serves **ONLY REST API endpoints**
- No Django templates rendered
- No HTML UI served
- Admin interface is development-only (can be disabled in production)
- Database operations
- Authentication & authorization
- Business logic

### Backend Deployment
```
https://leadsync-backend.frolix.site/
├── /api/auth/         ← Authentication endpoints
├── /api/leads/        ← Lead management endpoints
├── /api/categories/   ← Metadata endpoints
├── /api/plans/        ← Billing endpoints
├── /admin/            ← (Development only, disable in production)
└── /media/            ← User uploads
```

### Backend is Now API-Only
- Disabled Django template engine
- Removed all Django template URL routes
- Only REST API routes remain
- Admin interface kept for development (can be disabled)

---

## Frontend Architecture (React-Only)

### What Frontend Does
- **ALL UI rendering** (100% React)
- Communicates with backend via REST API calls
- Handles offline mode with IndexedDB
- Auto-sync when online
- User authentication (login/logout)
- All pages and components

### Frontend Deployment
```
https://leadsync.frolix.site/
├── /                    ← Home page
├── /login               ← Login form
├── /signup              ← Registration
├── /dashboard           ← Dashboard
├── /leads               ← Lead management
├── /templates           ← Lead templates
├── /analytics           ← Analytics
├── /settings            ← User settings
└── (all pages load from React, not server)
```

### Frontend Communicates Via API
```javascript
// Example: Frontend calls backend API
const response = await fetch('https://leadsync-backend.frolix.site/api/leads/', {
  method: 'GET',
  headers: {
    'Authorization': 'Bearer token...',
    'Content-Type': 'application/json'
  }
});
```

---

## Environment Setup

### Backend (.env)
```env
DEBUG=False  (production)
SECRET_KEY=your-secure-key
DATABASE_URL=postgresql://...
ALLOWED_HOSTS=leadsync-backend.frolix.site
CORS_ALLOWED_ORIGINS=https://leadsync.frolix.site

# API Configuration
REST_FRAMEWORK_PAGINATION=50
API_THROTTLE_RATE=1000/day
```

### Frontend (.env)
```env
VITE_API_URL=https://leadsync-backend.frolix.site/api
VITE_APP_NAME=LeadSync CRM
```

---

## API Endpoints

### Authentication
```
POST   /api/auth/login/              ← User login
POST   /api/auth/register/           ← User registration
POST   /api/auth/logout/             ← User logout
GET    /api/auth/user/               ← Current user
GET    /api/auth/profile/            ← User profile
```

### Leads (Main Feature)
```
GET    /api/leads/                   ← List leads (with pagination, filtering)
POST   /api/leads/                   ← Create lead
GET    /api/leads/{id}/              ← Get single lead
PUT    /api/leads/{id}/              ← Update lead
DELETE /api/leads/{id}/              ← Delete lead
PATCH  /api/leads/{id}/change_status/← Change lead status
POST   /api/leads/{id}/assign/       ← Assign lead to user
```

### Metadata
```
GET    /api/categories/              ← List categories
GET    /api/sources/                 ← List sources
GET    /api/owner-categories/        ← Owner's categories
GET    /api/owner-sources/           ← Owner's sources
```

### Analytics & Activity
```
GET    /api/dashboard/stats/         ← Dashboard statistics
GET    /api/leads/status-distribution/ ← Status breakdown
GET    /api/activity-logs/           ← Activity timeline
```

### Billing
```
GET    /api/plans/                   ← List pricing plans
GET    /api/billing/subscriptions/   ← User subscriptions
POST   /api/billing/checkout/        ← Create checkout session
```

---

## Data Flow

### User Registration Example
```
1. Frontend: User fills signup form
   ↓
2. Frontend: POST /api/auth/register/ { username, email, password }
   ↓
3. Backend: Validates data, creates user in database
   ↓
4. Backend: Returns JWT token
   ↓
5. Frontend: Stores token, redirects to dashboard
```

### Creating a Lead (Offline-Capable)
```
ONLINE:
1. Frontend: User fills lead form
2. Frontend: POST /api/leads/ { name, email, phone, ... }
3. Backend: Creates lead in database
4. Backend: Returns created lead
5. Frontend: Updates UI with new lead

OFFLINE:
1. Frontend: User fills lead form
2. Frontend: Saves to IndexedDB (offline database)
3. Frontend: Shows "Syncing..." status
4. Frontend: When online, POST /api/leads/
5. Backend: Creates lead in database
6. Frontend: Syncs and updates status to "Synced"
```

---

## Deployment

### Deploy Backend (Separate Server)
```bash
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic
gunicorn LeadSync.wsgi:application --bind 0.0.0.0:8000
```

**OR** deploy to Heroku/AWS/DigitalOcean as standalone Django app

### Deploy Frontend (Separate Server)
```bash
cd frontend
npm install
npm run build
# Deploy 'dist' folder to Vercel, Netlify, or your hosting
```

---

## Key Points

✅ **Completely Independent**
- Backend can be updated without redeploying frontend
- Frontend can be updated without touching backend
- Both scale independently

✅ **API-First Design**
- Backend is pure REST API
- No templates, no UI served by Django
- Frontend is 100% React

✅ **Offline Capability**
- Frontend works offline with IndexedDB
- Changes queued automatically
- Auto-sync when connection restored

✅ **Secure Separation**
- Backend validates all requests
- Frontend validates form inputs
- CORS properly configured
- JWT tokens for authentication

✅ **Easy to Test**
- Backend: Test API endpoints separately
- Frontend: Test UI/UX separately
- Integration tests verify API contracts

---

## File Structure

```
project/
├── backend/                    ← Django REST API
│   ├── LeadSync/               ← Django project settings
│   │   ├── settings.py         ✅ API-only (no templates)
│   │   └── urls.py             ✅ Only API routes
│   ├── core/
│   │   ├── api_views.py        ← API endpoints
│   │   ├── api_urls.py         ← API routing
│   │   └── serializers.py      ← Data validation
│   ├── accounts/
│   ├── billing/
│   └── manage.py
│
├── frontend/                   ← React App
│   ├── src/
│   │   ├── pages/              ← Page components
│   │   ├── components/         ← UI components
│   │   ├── services/
│   │   │   ├── api.ts          ← API client
│   │   │   ├── db.ts           ← Offline storage
│   │   │   └── sync.ts         ← Auto-sync logic
│   │   ├── context/            ← Auth context
│   │   └── App.tsx             ← Routing
│   └── package.json
│
└── Documentation files
```

---

## Common Issues & Solutions

### Issue: Backend still showing Django UI
**Solution**: Settings have been updated
- Templates disabled in `settings.py`
- Only API routes in `urls.py`
- Admin interface is development-only

### Issue: Frontend can't connect to backend
**Ensure**:
1. Backend running and accessible
2. CORS configured correctly (CORS_ALLOWED_ORIGINS)
3. Frontend using correct API URL in `.env`
4. No authentication required for public endpoints

### Issue: Offline sync not working
**Check**:
1. IndexedDB enabled in browser
2. Service Workers registered
3. Network status detection working
4. API endpoints accessible when online

---

## Next Steps

1. Deploy backend to dedicated server (Heroku/AWS/DigitalOcean)
2. Deploy frontend to Vercel/Netlify
3. Update `.env` files with production URLs
4. Test API endpoints with Postman
5. Test offline functionality
6. Monitor logs for issues

---

## Support

For issues with:
- **Backend API**: Check `/admin/` for data and logs
- **Frontend**: Check browser DevTools console
- **Connectivity**: Check CORS headers in browser Network tab
- **Offline**: Check Application tab → IndexedDB in DevTools

