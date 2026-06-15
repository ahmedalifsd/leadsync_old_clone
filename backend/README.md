# LeadSync CRM - Backend (Django REST API)

This is the Django backend for the LeadSync CRM system. It provides REST API endpoints for managing leads, users, teams, and billing.

## Prerequisites

- Python 3.8+
- PostgreSQL 12+
- pip or pipenv

## Installation

### 1. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the backend directory:

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com
CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://localhost:3000

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/leadsync

# CORS Configuration (Frontend URLs)
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000,https://yourdomain.com

# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@leadsync.com

# Stripe Configuration
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Google Analytics
GA_MEASUREMENT_ID=G-XXXXXXXX

# Support Info
SUPPORT_PHONE=+1234567890
SUPPORT_WHATSAPP=+1234567890
```

### 4. Database Setup

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
```

## Running the Development Server

```bash
python manage.py runserver 0.0.0.0:8000
```

The API will be available at `http://localhost:8000/api/`

## API Endpoints

### Authentication
- `POST /api/auth/login/` - User login
- `POST /api/auth/logout/` - User logout
- `GET /api/auth/user/` - Get current user
- `POST /api/auth/register/` - User registration

### Leads
- `GET /api/leads/` - List all leads
- `POST /api/leads/` - Create a new lead
- `GET /api/leads/{id}/` - Get lead details
- `PUT /api/leads/{id}/` - Update lead
- `DELETE /api/leads/{id}/` - Delete lead
- `GET /api/leads/{id}/activities/` - Get lead activities

### Teams
- `GET /api/teams/` - List user's teams
- `POST /api/teams/` - Create team
- `PUT /api/teams/{id}/` - Update team
- `GET /api/teams/{id}/members/` - List team members

### Categories
- `GET /api/categories/` - List categories
- `POST /api/categories/` - Create category

### Sources
- `GET /api/sources/` - List sources
- `POST /api/sources/` - Create source

### Billing
- `GET /api/billing/subscriptions/` - Get subscriptions
- `POST /api/billing/checkout/` - Create checkout session
- `POST /api/billing/invoice/manual-payment/` - Submit manual payment

## Project Structure

```
backend/
├── LeadSync/           # Main project configuration
│   ├── settings.py     # Django settings
│   ├── urls.py         # URL routing
│   └── wsgi.py         # WSGI application
├── accounts/           # User authentication & management
├── core/              # Lead management & main features
├── billing/           # Payment & subscription handling
├── team/              # Team management
├── static/            # Static files (CSS, JS, images)
├── manage.py          # Django CLI
└── requirements.txt   # Python dependencies
```

## Important Notes

- **Database**: The backend expects PostgreSQL. Update `DATABASES` in `LeadSync/settings.py` if using a different database.
- **Email**: Configure SMTP settings in `.env` for email notifications to work.
- **Stripe**: Add your Stripe API keys in `.env` for payment processing.
- **CORS**: Make sure to add your React frontend URL to `CORS_ALLOWED_ORIGINS` in `.env`.

## Deployment

### Using Gunicorn

```bash
pip install gunicorn
gunicorn LeadSync.wsgi:application --bind 0.0.0.0:8000
```

### Using Docker

A Dockerfile can be created for containerized deployment.

## Database Backups

```bash
# Create a backup
pg_dump -U postgres leadsync > backup.sql

# Restore from backup
psql -U postgres leadsync < backup.sql
```

## Troubleshooting

### Database Connection Error
- Ensure PostgreSQL is running
- Check credentials in `.env`
- Run migrations: `python manage.py migrate`

### CORS Errors
- Add your frontend URL to `CORS_ALLOWED_ORIGINS` in `.env`
- Restart the Django server

### Static Files Not Loading
- Run `python manage.py collectstatic`
- Check `STATIC_URL` and `STATIC_ROOT` in settings

## Support

For issues or questions, please contact the development team.
