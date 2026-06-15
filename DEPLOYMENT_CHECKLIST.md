# LeadSync CRM: Deployment Checklist

## Before Deployment

### Backend Checklist
- [ ] Django settings in API-only mode (✅ DONE)
  - [ ] Templates disabled
  - [ ] Only API routes enabled
  - [ ] Static files configured for media only

- [ ] Environment variables set
  - [ ] SECRET_KEY (secure, unique)
  - [ ] DEBUG=False
  - [ ] ALLOWED_HOSTS set correctly
  - [ ] DATABASE_URL configured
  - [ ] CORS_ALLOWED_ORIGINS set to frontend URL

- [ ] Database ready
  - [ ] PostgreSQL running and accessible
  - [ ] Migrations applied (`python manage.py migrate`)
  - [ ] Superuser created for admin access

- [ ] Security checked
  - [ ] ALLOWED_HOSTS configured
  - [ ] CSRF_TRUSTED_ORIGINS set
  - [ ] CORS properly configured
  - [ ] No debug mode in production
  - [ ] Secret key is secure

### Frontend Checklist
- [ ] Environment variables set
  - [ ] VITE_API_URL = backend API URL
  - [ ] VITE_APP_NAME = "LeadSync CRM"

- [ ] API configuration
  - [ ] API endpoint URLs correct
  - [ ] CORS headers accepted
  - [ ] Authentication tokens working

- [ ] Build tested
  - [ ] `npm run build` successful
  - [ ] `dist/` folder created
  - [ ] No console errors

- [ ] Functionality tested
  - [ ] Login works
  - [ ] API calls successful
  - [ ] Offline mode working
  - [ ] Auto-sync working

---

## Backend Deployment (Separate Server)

### Option 1: Heroku

```bash
cd backend

# Create Heroku app
heroku create leadsync-api

# Set environment variables
heroku config:set DEBUG=False
heroku config:set SECRET_KEY='your-secure-key'
heroku config:set DATABASE_URL='postgresql://...'
heroku config:set CORS_ALLOWED_ORIGINS='https://yourdomain.com'

# Deploy
git push heroku main

# Run migrations
heroku run python manage.py migrate

# Create superuser
heroku run python manage.py createsuperuser
```

### Option 2: AWS/DigitalOcean

```bash
# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate

# Start server with gunicorn
gunicorn LeadSync.wsgi:application --bind 0.0.0.0:8000
```

### Option 3: Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN python manage.py collectstatic --noinput

CMD ["gunicorn", "LeadSync.wsgi:application", "--bind", "0.0.0.0:8000"]
```

---

## Frontend Deployment (Vercel - Recommended)

### Deploy to Vercel

```bash
cd frontend

# Install Vercel CLI
npm install -g vercel

# Login to Vercel
vercel login

# Deploy
vercel

# Set environment variables in Vercel dashboard
# - VITE_API_URL
# - VITE_APP_NAME
```

### Alternative: Netlify

```bash
cd frontend

# Build
npm run build

# Deploy dist folder to Netlify
# Via CLI: npm install -g netlify-cli && netlify deploy --prod --dir=dist
```

---

## Post-Deployment Testing

### Test Backend API
```bash
# Test login endpoint
curl -X POST http://backend-url/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}'

# Test leads endpoint
curl -X GET http://backend-url/api/leads/ \
  -H "Authorization: Bearer <token>"

# Test CORS headers
curl -i -X OPTIONS http://backend-url/api/leads/
```

### Test Frontend
1. Open https://frontend-url in browser
2. Test login
3. Test lead creation
4. Test offline mode (DevTools → Network → Offline)
5. Test sync when back online

---

## Production Monitoring

### Backend
- Monitor database connections
- Check API response times
- Monitor error rates
- Set up logging (Sentry/LogRocket)

### Frontend
- Monitor page load times
- Check JavaScript errors (Sentry)
- Monitor user engagement
- Check API connectivity issues

---

## URLs Configuration

Update these in production:

### Backend Environment
```env
# Production
ALLOWED_HOSTS=leadsync-backend.yourdomain.com
CORS_ALLOWED_ORIGINS=https://leadsync.yourdomain.com
DATABASE_URL=postgresql://prod_user:pass@prod_host/leadsync_db
```

### Frontend Environment (Vercel)
```env
VITE_API_URL=https://leadsync-backend.yourdomain.com/api
VITE_APP_NAME=LeadSync CRM
```

---

## Troubleshooting

### Backend not responding
- Check server is running
- Check firewall rules
- Check database connection
- Check logs for errors

### Frontend can't connect to API
- Check CORS headers in browser Network tab
- Verify VITE_API_URL is correct
- Check backend is accessible
- Check authentication token validity

### Offline sync not working
- Check IndexedDB in browser DevTools
- Check Service Worker registration
- Verify network detection
- Check API endpoint accessibility

---

## Quick Start

### 1. Deploy Backend First
```bash
cd backend
# Set up your server/hosting
# Configure .env with production values
# Deploy and test API endpoints
```

### 2. Deploy Frontend
```bash
cd frontend
# Update .env with backend API URL
npm run build
# Deploy dist folder to Vercel/Netlify
```

### 3. Test Everything
- Login page works
- Create a lead
- Go offline and create another lead
- Come back online and verify sync
- Check admin panel for data

### 4. Monitor
- Set up error tracking (Sentry)
- Monitor API response times
- Check user engagement
- Review logs regularly
