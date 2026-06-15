# LeadSync CRM - Complete Setup Guide

This guide explains how to set up both the Django backend and React frontend for the LeadSync CRM system.

## Project Structure

```
leadsync_old_clone/
├── backend/                 # Django REST API (separate server)
│   ├── LeadSync/           # Project settings
│   ├── accounts/           # User management
│   ├── core/               # Lead management
│   ├── billing/            # Payments
│   ├── team/               # Team management
│   ├── requirements.txt    # Python dependencies
│   ├── manage.py           # Django CLI
│   └── README.md           # Backend setup instructions
│
├── frontend/               # React + TypeScript (for Vercel/hosting)
│   ├── src/               # React source code
│   ├── public/            # Static assets
│   ├── package.json       # Node dependencies
│   ├── vite.config.ts     # Vite configuration
│   └── README.md          # Frontend setup instructions
│
├── SETUP.md               # This file
└── Other files (original Django project files - can be archived)
```

## Quick Start (Development)

### Backend Setup (Django REST API)

```bash
# Navigate to backend folder
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://localhost:3000
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
DATABASE_URL=postgresql://user:password@localhost:5432/leadsync
EOF

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Start server
python manage.py runserver 0.0.0.0:8000
```

Backend will run at: **http://localhost:8000**

### Frontend Setup (React)

In a new terminal:

```bash
# Navigate to frontend folder
cd frontend

# Install dependencies
npm install

# Create .env file
cat > .env << EOF
VITE_API_URL=http://localhost:8000/api
VITE_APP_NAME=LeadSync CRM
EOF

# Start development server
npm run dev
```

Frontend will run at: **http://localhost:5173**

## Key Configuration Points

### Backend Configuration (.env)

| Variable | Purpose | Example |
|----------|---------|---------|
| `SECRET_KEY` | Django security key | Auto-generated |
| `DEBUG` | Debug mode | `True` (dev only) |
| `DATABASE_URL` | PostgreSQL connection | `postgresql://user:pass@localhost/leadsync` |
| `ALLOWED_HOSTS` | Allowed domain names | `localhost,127.0.0.1,yourdomain.com` |
| `CORS_ALLOWED_ORIGINS` | Frontend URLs (CRITICAL) | `http://localhost:5173,https://yourdomain.com` |
| `STRIPE_PUBLISHABLE_KEY` | Stripe payment key | `pk_test_...` |
| `STRIPE_SECRET_KEY` | Stripe secret key | `sk_test_...` |

### Frontend Configuration (.env)

| Variable | Purpose | Example |
|----------|---------|---------|
| `VITE_API_URL` | Backend API URL | `http://localhost:8000/api` |
| `VITE_APP_NAME` | App name | `LeadSync CRM` |

## Database Setup

### PostgreSQL Installation

**macOS (Homebrew)**
```bash
brew install postgresql
brew services start postgresql
createdb leadsync
```

**Ubuntu/Debian**
```bash
sudo apt-get install postgresql postgresql-contrib
sudo -u postgres createdb leadsync
```

**Windows**
- Download from [postgresql.org](https://www.postgresql.org/download/windows/)
- Follow installer, remember the password

### Apply Migrations

```bash
cd backend
python manage.py migrate
```

## Offline-First Capabilities

The React frontend is built with offline-first capability:

1. **IndexedDB Storage**: All leads are cached locally in browser
2. **Service Workers**: Enables offline access to cached data
3. **Sync Queue**: All changes are queued when offline
4. **Auto Sync**: When internet returns, changes sync automatically

### Testing Offline Mode

1. Open DevTools (F12)
2. Go to **Application > Service Workers**
3. Check "Offline" to simulate offline mode
4. Try adding/editing/deleting leads
5. Uncheck "Offline" to restore internet
6. Watch data sync automatically

## API Endpoints

The Django backend provides these REST endpoints:

### Authentication
```
POST   /api/auth/login/                - Login
POST   /api/auth/logout/               - Logout
GET    /api/auth/user/                 - Current user
POST   /api/auth/register/             - Register
```

### Leads (Main CRUD)
```
GET    /api/leads/                     - List all leads
POST   /api/leads/                     - Create lead
GET    /api/leads/{id}/                - Get lead details
PUT    /api/leads/{id}/                - Update lead
PATCH  /api/leads/{id}/                - Partial update
DELETE /api/leads/{id}/                - Delete lead
GET    /api/leads/{id}/activities/     - Get lead activities
```

### Teams
```
GET    /api/teams/                     - List teams
POST   /api/teams/                     - Create team
GET    /api/teams/{id}/                - Team details
PUT    /api/teams/{id}/                - Update team
GET    /api/teams/{id}/members/        - Team members
```

### Other Resources
```
GET    /api/categories/                - List categories
POST   /api/categories/                - Create category
GET    /api/sources/                   - List sources
POST   /api/sources/                   - Create source
GET    /api/billing/subscriptions/     - User subscriptions
```

## Deployment

### Backend Deployment (Django)

**Heroku**
```bash
heroku create your-app-name
heroku addons:create heroku-postgresql:standard-0
git push heroku main
heroku run python manage.py migrate
```

**Your Own Server**
```bash
# Using Gunicorn
gunicorn LeadSync.wsgi:application --bind 0.0.0.0:8000

# Using Docker
docker build -t leadsync-backend .
docker run -p 8000:8000 leadsync-backend
```

### Frontend Deployment (React)

**Vercel (Recommended)**
```bash
npm install -g vercel
vercel
# Update VITE_API_URL to your production backend
```

**Netlify**
```bash
npm run build
# Deploy dist/ folder
```

**Docker**
```bash
docker build -t leadsync-frontend .
docker run -p 3000:3000 leadsync-frontend
```

## Common Issues & Solutions

### CORS Errors

**Error**: `Access to XMLHttpRequest blocked by CORS policy`

**Solution**: Add your frontend URL to `CORS_ALLOWED_ORIGINS` in backend `.env`:
```env
CORS_ALLOWED_ORIGINS=http://localhost:5173,https://yourdomain.com
```

Then restart Django server.

### Database Connection Failed

**Error**: `connection refused` or `could not connect to server`

**Solution**:
1. Ensure PostgreSQL is running
2. Check credentials in `DATABASE_URL`
3. Create database: `createdb leadsync`
4. Run migrations: `python manage.py migrate`

### API Endpoint Not Found (404)

**Error**: `404 Not Found` for API routes

**Solution**:
- Check endpoint URL in frontend matches backend
- Run `python manage.py show_urls` to list all routes
- Verify REST framework is installed: `pip install djangorestframework`

### Data Not Syncing Offline

**Solution**:
1. Open DevTools → Application → Service Workers
2. Check "Offline" is enabled for testing
3. Check IndexedDB has cached data
4. Review browser console for sync errors

## Development Workflow

1. **Backend Changes**
   - Modify Django code in `backend/`
   - Restart Django server
   - Test API endpoints with Postman or curl

2. **Frontend Changes**
   - Modify React code in `frontend/src/`
   - Hot Module Replacement (HMR) auto-refreshes
   - Test in browser

3. **Database Changes**
   ```bash
   cd backend
   python manage.py makemigrations
   python manage.py migrate
   ```

4. **Adding New Features**
   - Create API endpoint in backend first
   - Test with Postman
   - Build React component to consume API
   - Test offline functionality

## Next Steps

1. **Read Backend README**: `cd backend && cat README.md`
2. **Read Frontend README**: `cd frontend && cat README.md`
3. **Start Development**:
   - Terminal 1: `cd backend && python manage.py runserver`
   - Terminal 2: `cd frontend && npm run dev`
4. **Test Offline**: Open DevTools and simulate offline mode
5. **Deploy**: Follow deployment instructions above

## Support & Troubleshooting

- **Backend Issues**: Check `backend/README.md`
- **Frontend Issues**: Check `frontend/README.md`
- **API Issues**: Use Postman to test endpoints
- **Database Issues**: Check PostgreSQL logs
- **Offline Issues**: Check browser DevTools

## Architecture Overview

```
User Browser
    ↓
React Frontend (localhost:5173)
    ├── IndexedDB (Offline Data)
    ├── Service Worker (Offline Support)
    └── Sync Manager (Auto-sync)
        ↓
API Client (Axios)
    ↓
Django REST API (localhost:8000)
    ├── Authentication
    ├── Lead CRUD
    ├── Team Management
    ├── Billing
    └── Database (PostgreSQL)
```

## File Organization

- **Keep separate**: Backend and Frontend are in different folders for independent deployment
- **Backend**: Push to your Django server
- **Frontend**: Push to Vercel/Netlify/your hosting
- **No coupling**: They communicate only via REST API

This setup allows you to:
- ✅ Deploy backend and frontend independently
- ✅ Scale each separately
- ✅ Use different hosting providers
- ✅ Maintain offline functionality
- ✅ Add more frontend apps (web, mobile, desktop) with same backend
