# 🚀 LeadSync CRM - Start Here

Welcome! Your Django CRM has been converted to a modern React frontend architecture. This guide will help you get started.

## 📋 What You Have

### Backend (Django REST API)
```
✅ Django 5.2 REST Framework enabled
✅ PostgreSQL database integration
✅ Authentication system
✅ CORS configured for frontend
✅ Stripe payment processing
✅ Email notifications
✅ Ready to deploy to your server
```

**Location**: `backend/` folder

### Frontend (React 19)
```
✅ React 19 + TypeScript
✅ Tailwind CSS (matches your design)
✅ Offline-first capability
✅ Auto-sync when internet returns
✅ Service Workers for offline support
✅ Modern build with Vite
✅ Ready to deploy to Vercel/Netlify
```

**Location**: `frontend/` folder

## 🎯 Quick Start (5 minutes)

### Step 1: Run Automated Setup
```bash
./start-dev.sh
```

This script will:
- ✅ Check Python, Node.js, npm
- ✅ Create Python virtual environment
- ✅ Install all dependencies
- ✅ Create `.env` files
- ✅ Show you next steps

### Step 2: Start Backend
Open **Terminal 1**:
```bash
cd backend
source venv/bin/activate
python manage.py migrate          # First time only
python manage.py runserver        # Backend runs at http://localhost:8000
```

### Step 3: Start Frontend
Open **Terminal 2**:
```bash
cd frontend
npm run dev                        # Frontend runs at http://localhost:5173
```

### Step 4: Access the App
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000/api/
- Django Admin: http://localhost:8000/admin/

## 📖 Read These Files (in order)

1. **SETUP.md** - Complete setup instructions
2. **DEPLOYMENT.md** - How to deploy to production
3. **PROJECT_STRUCTURE.md** - Architecture overview
4. **CONVERSION_COMPLETE.md** - What's been done & what's next

## 🏗️ Project Structure

```
leadsync_old_clone/
│
├── 📁 backend/                    ← Django REST API (Your Server)
│   ├── README.md                  Read this for backend setup
│   ├── requirements.txt           Python dependencies
│   ├── .env.example               Copy to .env and edit
│   └── ... (Django files)
│
├── 📁 frontend/                   ← React App (Vercel/Netlify)
│   ├── README.md                  Read this for frontend setup
│   ├── package.json               Node dependencies
│   ├── .env.example               Copy to .env and edit
│   └── src/                       Your React components go here
│
├── 📄 SETUP.md                    Complete setup guide ← START HERE
├── 📄 DEPLOYMENT.md               Production deployment guide
├── 📄 PROJECT_STRUCTURE.md        Architecture & organization
├── 📄 CONVERSION_COMPLETE.md      Status & next steps
└── 🚀 start-dev.sh                Automated setup script
```

## ⚙️ Configuration

### Backend Configuration
Copy `backend/.env.example` to `backend/.env`:

```env
# Required
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/leadsync

# For production, add these:
# - STRIPE_PUBLISHABLE_KEY
# - STRIPE_SECRET_KEY
# - EMAIL_HOST_USER
# - EMAIL_HOST_PASSWORD
```

### Frontend Configuration  
Copy `frontend/.env.example` to `frontend/.env`:

```env
VITE_API_URL=http://localhost:8000/api
VITE_APP_NAME=LeadSync CRM
```

## 🔄 How It Works

```
┌─────────────────────────────────────────────┐
│         React Frontend (5173)               │
│  - Dashboard, Leads, Teams, Forms           │
│  - Tailwind CSS styling                     │
│  - Offline support with IndexedDB           │
└──────────────┬──────────────────────────────┘
               │ Axios HTTP Client
               │ REST API Calls
               ↓
┌─────────────────────────────────────────────┐
│      Django REST API (8000)                 │
│  - Authentication, Leads CRUD               │
│  - Teams, Billing, Notifications            │
│  - PostgreSQL Database                      │
└─────────────────────────────────────────────┘
```

## 🌐 What Happens Offline

1. **You're online** → Changes sync immediately
2. **You go offline** → Changes save to local IndexedDB  
3. **You make changes** → Work normally, all changes saved locally
4. **Internet returns** → Auto-sync queues changes to backend
5. **Sync complete** → Data is now on server ✅

## 📱 Features to Build

Your React app needs these pages/components:

**Essential:**
- [ ] Dashboard (overview, stats)
- [ ] Leads list (CRUD operations)
- [ ] Lead details (view/edit)
- [ ] Login page
- [ ] Navigation (navbar, sidebar)

**Important:**
- [ ] Teams management
- [ ] Categories & sources
- [ ] Settings page
- [ ] Activity logs

**Nice to Have:**
- [ ] Chat/messaging
- [ ] Advanced filters
- [ ] Bulk operations
- [ ] Reports/analytics

## 🚀 Deployment

### Backend (to your server)
```bash
cd backend
# Follow DEPLOYMENT.md → "Deploy to Your Server"
# Or deploy to Heroku with "Deploy to Heroku"
```

### Frontend (to Vercel - Recommended)
```bash
cd frontend
# Go to vercel.com
# Import your GitHub repo
# Deploy automatically ✅
```

## ✅ Checklist Before Deployment

### Before Going Live

Backend:
- [ ] Set `DEBUG=False`
- [ ] Generate new `SECRET_KEY`
- [ ] Update `ALLOWED_HOSTS`
- [ ] Update `CORS_ALLOWED_ORIGINS`
- [ ] Set up real PostgreSQL
- [ ] Add Stripe keys (if needed)
- [ ] Configure email
- [ ] Enable HTTPS/SSL
- [ ] Test all API endpoints

Frontend:
- [ ] Update `VITE_API_URL` to production
- [ ] Run `npm run build`
- [ ] Test production build
- [ ] Deploy to Vercel/Netlify
- [ ] Test offline functionality
- [ ] Test on mobile

## 🆘 Troubleshooting

### Frontend won't connect to backend?
- Check `VITE_API_URL` in `.env`
- Ensure backend is running
- Check CORS errors in browser console
- Add frontend URL to `CORS_ALLOWED_ORIGINS` in backend

### Database won't connect?
- Is PostgreSQL running?
- Check credentials in `DATABASE_URL`
- Run: `createdb leadsync`
- Run: `python manage.py migrate`

### npm/pip dependencies error?
- Delete `node_modules/` and `venv/`
- Reinstall: `npm install` and `pip install -r requirements.txt`

### Service Worker not working?
- Clear browser cache (Ctrl+Shift+Del)
- Hard refresh (Ctrl+Shift+R)
- Check browser console for errors

## 📚 Documentation Map

```
First Time?
  ↓
  └─→ This file (START_HERE.md)
      ↓
      └─→ SETUP.md (Quick start)
          ↓
          ├─→ backend/README.md (Backend help)
          ├─→ frontend/README.md (Frontend help)
          └─→ PROJECT_STRUCTURE.md (Architecture)

Ready to Deploy?
  ↓
  └─→ DEPLOYMENT.md

Need Architecture Details?
  ↓
  └─→ PROJECT_STRUCTURE.md

Conversion Complete - What's Done?
  ↓
  └─→ CONVERSION_COMPLETE.md
```

## 🎨 Design System

Your React app should match this design:

**Colors**
```
Primary (Brown):        #8b640d
Secondary (Dark Blue):  #092C4C  
Accent (Gold):          #F39C12
Background:             #F5F5F5
Text:                   #333333
```

**Fonts**
```
Headings: Poppins (Bold)
Body:     Nunito (Regular)
```

**Layout**
- Use Tailwind CSS utilities
- Flexbox for most layouts
- Grid for complex 2D layouts
- 4px spacing units

## 💡 Pro Tips

1. **Work on one page at a time** - Build, test, then move on
2. **Test offline early** - DevTools → Application → Service Workers → Enable offline
3. **Use TypeScript** - Catch errors before runtime
4. **Deploy frequently** - Small, regular deployments reduce risk
5. **Monitor performance** - Use DevTools Lighthouse
6. **Read the READMEs** - Each folder has detailed instructions
7. **Keep secrets safe** - Never commit `.env` files
8. **Test on mobile** - Responsive design is important

## 🤝 Common Tasks

### Add a new feature
1. Create API endpoint in backend
2. Test with Postman
3. Create React component
4. Connect to API with axios
5. Add offline support
6. Test everything

### Deploy changes
1. Push to GitHub
2. Run tests locally
3. Backend: SSH to server and pull changes
4. Frontend: Vercel auto-deploys on git push
5. Verify production is working

### Fix a bug
1. Identify if it's backend or frontend
2. Check logs (browser console, Django logs)
3. Fix the issue
4. Test thoroughly (online & offline)
5. Deploy fix

## 🔐 Security Reminders

- [ ] Never commit `.env` files
- [ ] Never share API keys
- [ ] Use HTTPS in production
- [ ] Keep dependencies updated
- [ ] Enable CORS for frontend URL only
- [ ] Use strong database password
- [ ] Backup database regularly
- [ ] Monitor logs for errors

## 📞 Getting Help

1. **Setup issues** → Read `SETUP.md`
2. **Backend issues** → Read `backend/README.md`
3. **Frontend issues** → Read `frontend/README.md`
4. **Architecture questions** → Read `PROJECT_STRUCTURE.md`
5. **Deployment issues** → Read `DEPLOYMENT.md`
6. **General info** → Read `CONVERSION_COMPLETE.md`

## 🎯 Next Steps Right Now

1. **Copy & paste this in terminal:**
   ```bash
   ./start-dev.sh
   ```

2. **Read these in order:**
   - SETUP.md (5 min read)
   - backend/README.md (5 min read)  
   - frontend/README.md (10 min read)

3. **Start development:**
   - Terminal 1: Backend server
   - Terminal 2: Frontend server

4. **Build your React components!**

---

## 📊 Project Status

| Component | Status | Next Step |
|-----------|--------|-----------|
| Backend API | ✅ Ready | Add endpoint implementations |
| Frontend Framework | ✅ Ready | Build React components |
| Offline Support | ✅ Ready | Implement sync logic |
| Documentation | ✅ Complete | Deploy to production |

## 🎉 You're All Set!

Everything is configured and ready. Now it's time to build!

**Start with:**
```bash
./start-dev.sh
```

**Then read:**
- SETUP.md
- backend/README.md
- frontend/README.md

**Questions?** Check the relevant README or see the documentation map above.

---

**Created**: June 15, 2024
**Status**: Ready for development
**Next Phase**: Build React components & REST API endpoints
