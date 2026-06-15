#!/bin/bash

# LeadSync CRM - Development Quick Start Script
# This script sets up and starts both backend and frontend

set -e  # Exit on error

echo "======================================"
echo "LeadSync CRM - Development Setup"
echo "======================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}→${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check Prerequisites
print_status "Checking prerequisites..."

# Check Python
if ! command -v python3 &> /dev/null; then
    print_warning "Python 3 not found. Please install Python 3.8+"
    exit 1
fi
print_success "Python 3 found: $(python3 --version)"

# Check Node.js
if ! command -v node &> /dev/null; then
    print_warning "Node.js not found. Please install Node.js 16+"
    exit 1
fi
print_success "Node.js found: $(node --version)"

# Check npm
if ! command -v npm &> /dev/null; then
    print_warning "npm not found. Please install npm"
    exit 1
fi
print_success "npm found: $(npm --version)"

# Check PostgreSQL
if ! command -v psql &> /dev/null; then
    print_warning "PostgreSQL not found. Some features may not work locally"
    echo "  Install from: https://www.postgresql.org/download/"
fi

echo ""
echo "======================================"
echo "Setup Backend"
echo "======================================"
echo ""

# Backend Setup
if [ ! -d "backend/venv" ]; then
    print_status "Creating Python virtual environment..."
    cd backend
    python3 -m venv venv
    print_success "Virtual environment created"
else
    print_success "Virtual environment exists"
    cd backend
fi

# Activate venv
print_status "Activating virtual environment..."
source venv/bin/activate || . venv/Scripts/activate 2>/dev/null
print_success "Virtual environment activated"

# Install Python dependencies
print_status "Installing Python dependencies..."
pip install -q -r requirements.txt
print_success "Python dependencies installed"

# Check if .env exists
if [ ! -f ".env" ]; then
    print_warning ".env file not found"
    print_status "Creating .env from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_success ".env created (please update with your values)"
    fi
fi

cd ..
echo ""
echo "======================================"
echo "Setup Frontend"
echo "======================================"
echo ""

# Frontend Setup
cd frontend

if [ ! -d "node_modules" ]; then
    print_status "Installing Node.js dependencies..."
    npm install
    print_success "Node dependencies installed"
else
    print_success "Node dependencies already installed"
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    print_warning ".env file not found"
    print_status "Creating .env from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_success ".env created"
    fi
fi

cd ..

echo ""
echo "======================================"
echo "Setup Complete!"
echo "======================================"
echo ""
echo "To start development servers, open two terminals:"
echo ""
echo -e "${YELLOW}Terminal 1 - Backend (Django REST API):${NC}"
echo "  cd backend"
echo "  source venv/bin/activate  # or: venv\\Scripts\\activate (Windows)"
echo "  python manage.py migrate  # (first time only)"
echo "  python manage.py runserver 0.0.0.0:8000"
echo ""
echo -e "${YELLOW}Terminal 2 - Frontend (React):${NC}"
echo "  cd frontend"
echo "  npm run dev"
echo ""
echo -e "${GREEN}Backend will run at:${NC} http://localhost:8000"
echo -e "${GREEN}Frontend will run at:${NC} http://localhost:5173"
echo ""
echo "======================================"
echo "Documentation"
echo "======================================"
echo ""
echo "  SETUP.md              - Complete setup instructions"
echo "  DEPLOYMENT.md         - Production deployment guide"
echo "  PROJECT_STRUCTURE.md  - Project organization overview"
echo "  backend/README.md     - Backend specific guide"
echo "  frontend/README.md    - Frontend specific guide"
echo ""
echo "======================================"
echo ""
