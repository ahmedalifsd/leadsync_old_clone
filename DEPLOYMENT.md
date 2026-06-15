# LeadSync CRM - Deployment Guide

This guide covers deploying both the Django backend and React frontend to production.

## Architecture

```
Your Server (Backend)          Vercel/Netlify (Frontend)
┌──────────────────┐          ┌──────────────────────┐
│  Django REST API │ ◄────────│  React Frontend      │
│  - PostgreSQL    │  (HTTPS) │  - Tailwind CSS      │
│  - Stripe        │          │  - Offline Support   │
│  - Email         │          │  - Auto-sync         │
└──────────────────┘          └──────────────────────┘
```

## Backend Deployment (Django REST API)

### Option 1: Deploy to Your Server (Recommended)

#### Step 1: Prepare Backend

```bash
cd backend

# Create production .env file
nano .env
# Copy from .env.example and update with production values:
# - DEBUG=False
# - SECRET_KEY=generate-new-secret-key
# - ALLOWED_HOSTS=yourdomain.com
# - DATABASE_URL=production-database-url
# - CORS_ALLOWED_ORIGINS=https://yourdomain.com
```

#### Step 2: Install on Server

```bash
# SSH into your server
ssh user@your-server.com

# Clone repository
git clone https://github.com/yourusername/leadsync_old_clone.git
cd leadsync_old_clone/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

#### Step 3: Set Up with Gunicorn & Nginx

**Install Gunicorn**
```bash
pip install gunicorn
```

**Create Systemd Service** (`/etc/systemd/system/leadsync.service`)

```ini
[Unit]
Description=LeadSync CRM Backend
After=network.target

[Service]
Type=notify
User=www-data
WorkingDirectory=/home/user/leadsync_old_clone/backend
ExecStart=/home/user/leadsync_old_clone/backend/venv/bin/gunicorn \
          --workers 3 \
          --bind 127.0.0.1:8000 \
          LeadSync.wsgi:application

[Install]
WantedBy=multi-user.target
```

**Start Service**
```bash
sudo systemctl start leadsync
sudo systemctl enable leadsync
```

**Configure Nginx** (`/etc/nginx/sites-available/leadsync`)

```nginx
upstream leadsync {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name api.yourdomain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # Static Files
    location /static/ {
        alias /home/user/leadsync_old_clone/backend/staticfiles/;
        expires 30d;
    }
    
    # Media Files
    location /media/ {
        alias /home/user/leadsync_old_clone/backend/media/;
        expires 7d;
    }
    
    # API Proxy
    location / {
        proxy_pass http://leadsync;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
}
```

**Enable Nginx Site**
```bash
sudo ln -s /etc/nginx/sites-available/leadsync /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

**Setup SSL with Let's Encrypt**
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot certonly --nginx -d api.yourdomain.com
```

#### Step 4: Database Backups

**Automated Daily Backups**
```bash
# Create backup script: /home/user/backup_db.sh
#!/bin/bash
BACKUP_DIR="/home/user/backups"
mkdir -p $BACKUP_DIR
pg_dump leadsync | gzip > $BACKUP_DIR/leadsync_$(date +%Y%m%d_%H%M%S).sql.gz

# Keep only last 30 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
```

**Add to Crontab**
```bash
crontab -e
# Add: 0 2 * * * /home/user/backup_db.sh
```

### Option 2: Deploy to Heroku

```bash
cd backend

# Install Heroku CLI
curl https://cli.heroku.com/install.sh | sh

# Login to Heroku
heroku login

# Create app
heroku create your-app-name

# Add PostgreSQL
heroku addons:create heroku-postgresql:standard-0

# Set environment variables
heroku config:set \
  SECRET_KEY=your-secret-key \
  DEBUG=False \
  ALLOWED_HOSTS=your-app-name.herokuapp.com

# Deploy
git push heroku main

# Run migrations
heroku run python manage.py migrate

# Create superuser
heroku run python manage.py createsuperuser

# View logs
heroku logs --tail
```

## Frontend Deployment (React)

### Option 1: Deploy to Vercel (Recommended)

**Step 1: Push to GitHub**
```bash
# In frontend directory
git remote add origin https://github.com/yourusername/leadsync-frontend.git
git push -u origin main
```

**Step 2: Deploy to Vercel**
- Go to [vercel.com](https://vercel.com)
- Click "Import Project"
- Select your GitHub repository
- Set project root to `frontend/`
- Add environment variables:
  ```
  VITE_API_URL=https://api.yourdomain.com/api
  VITE_APP_NAME=LeadSync CRM
  ```
- Click Deploy

**Step 3: Custom Domain**
- Go to Vercel Dashboard → Project Settings → Domains
- Add your domain
- Update DNS records as instructed

### Option 2: Deploy to Netlify

```bash
cd frontend

# Build for production
npm run build

# Install Netlify CLI
npm install -g netlify-cli

# Deploy
netlify deploy --prod --dir=dist
```

Or drag & drop `dist/` folder in Netlify Dashboard.

### Option 3: Deploy to Your Server

**Build**
```bash
cd frontend
npm run build
# Creates optimized dist/ folder
```

**Configure Nginx**
```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    root /home/user/leadsync_old_clone/frontend/dist;
    index index.html;
    
    # Enable gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;
    
    # Cache static files
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # Route all requests to index.html (SPA)
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

## Post-Deployment Checklist

### Backend
- [ ] Set `DEBUG=False` in production
- [ ] Use strong `SECRET_KEY`
- [ ] Enable HTTPS with SSL certificate
- [ ] Configure PostgreSQL with strong password
- [ ] Set up database backups
- [ ] Configure Stripe with production keys
- [ ] Set up email notifications
- [ ] Test API endpoints with production domain
- [ ] Monitor logs: `tail -f /var/log/syslog`
- [ ] Set up error tracking (Sentry recommended)

### Frontend
- [ ] Update `VITE_API_URL` to production backend
- [ ] Enable HTTPS
- [ ] Set up CDN for static files
- [ ] Configure analytics
- [ ] Test offline functionality in production
- [ ] Test on multiple browsers & devices
- [ ] Monitor performance with PageSpeed Insights

## Production Environment Variables

### Backend (.env)
```env
SECRET_KEY=generate-new-with-secrets-module
DEBUG=False
ALLOWED_HOSTS=api.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com
DATABASE_URL=postgresql://user:secure-password@db-host:5432/leadsync
CORS_ALLOWED_ORIGINS=https://yourdomain.com
EMAIL_HOST_USER=noreply@yourdomain.com
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_SECRET_KEY=sk_live_...
```

### Frontend (.env)
```env
VITE_API_URL=https://api.yourdomain.com/api
VITE_APP_NAME=LeadSync CRM
```

## Monitoring & Maintenance

### Health Checks
```bash
# Check backend health
curl https://api.yourdomain.com/api/auth/user/

# Check frontend is serving
curl https://yourdomain.com/
```

### Logs
```bash
# Django logs
tail -f /var/log/syslog | grep gunicorn

# Nginx logs
tail -f /var/log/nginx/error.log
tail -f /var/log/nginx/access.log
```

### Database Maintenance
```bash
# Vacuum database
psql leadsync -c "VACUUM ANALYZE;"

# Check database size
psql leadsync -c "SELECT pg_size_pretty(pg_database_size('leadsync'));"
```

## Scaling

### Horizontal Scaling
1. **Multiple Gunicorn Workers**: Increase `--workers` in systemd service
2. **Load Balancer**: Use Nginx with upstream servers
3. **Caching**: Redis for session storage
4. **CDN**: Cloudflare for static files & DDoS protection

### Database Scaling
1. **Read Replicas**: PostgreSQL streaming replication
2. **Connection Pooling**: Use PgBouncer
3. **Partitioning**: Partition large tables
4. **Indexing**: Add database indexes for slow queries

## Troubleshooting

### CORS Errors in Production
- Ensure frontend domain is in `CORS_ALLOWED_ORIGINS`
- Restart Gunicorn: `sudo systemctl restart leadsync`

### Static Files Not Loading
- Run: `python manage.py collectstatic --noinput`
- Check Nginx `root` and `alias` paths

### Database Connection Issues
- Check PostgreSQL is running and accepting connections
- Verify credentials in `DATABASE_URL`
- Check firewall rules

### High CPU/Memory Usage
- Monitor with: `top`, `htop`, `ps aux`
- Increase Gunicorn workers or Nginx worker processes
- Consider caching with Redis

## Security Recommendations

1. **HTTPS Only**: Force HTTPS redirects
2. **Security Headers**: Add security headers in Nginx
3. **Rate Limiting**: Enable in Nginx or use fail2ban
4. **Database**: Use strong passwords, restrict IP access
5. **Secrets**: Use environment variables, never commit secrets
6. **Updates**: Keep Django, dependencies, and OS updated
7. **Firewall**: Configure UFW or AWS security groups
8. **Backups**: Regular automated backups to separate location

## Support

For deployment issues, check:
- Backend logs: `sudo journalctl -u leadsync -f`
- Nginx logs: `/var/log/nginx/`
- Django logs: Application output
- PostgreSQL logs: `/var/log/postgresql/`
