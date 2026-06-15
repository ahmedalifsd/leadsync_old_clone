# LeadSync CRM - Frontend (React + Tailwind)

A modern React frontend for the LeadSync CRM system with offline-first capabilities, automatic data synchronization, and exact UI replication from the original Django template.

## Features

- ✅ **Offline-First**: Full functionality works offline (add/edit/delete leads)
- ✅ **Auto Sync**: Automatically syncs data when internet is restored
- ✅ **Real-time Updates**: Live data synchronization with backend
- ✅ **Responsive Design**: Works seamlessly on desktop, tablet, and mobile
- ✅ **Same Design**: Pixel-perfect replication of original Django UI
- ✅ **Fast Performance**: Optimized bundle size and rendering
- ✅ **TypeScript**: Type-safe development with full TypeScript support

## Tech Stack

- **React 19** - UI framework
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling with utility classes
- **Vite** - Fast build tool
- **Axios** - HTTP client
- **React Query** - Server state management & caching
- **Dexie.js** - IndexedDB wrapper for offline storage
- **Service Worker** - Offline support via Workbox

## Prerequisites

- Node.js 16+ (recommended 18+)
- npm or yarn package manager
- Backend API running (see ../backend/README.md)

## Installation

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure Environment Variables

Create a `.env` file in the frontend directory:

```env
VITE_API_URL=http://localhost:8000/api
VITE_APP_NAME=LeadSync CRM
```

For production:

```env
VITE_API_URL=https://api.yourdomain.com/api
VITE_APP_NAME=LeadSync CRM
```

### 3. Start Development Server

```bash
npm run dev
```

The app will be available at `http://localhost:5173`

## Project Structure

```
frontend/
├── src/
│   ├── components/          # Reusable UI components
│   │   ├── Layout.tsx       # Main layout wrapper
│   │   ├── Navbar.tsx       # Navigation bar
│   │   ├── Sidebar.tsx      # Sidebar navigation
│   │   ├── Dashboard.tsx    # Dashboard page
│   │   ├── LeadForm.tsx     # Lead creation/edit form
│   │   ├── LeadList.tsx     # Leads table/grid
│   │   └── ...
│   ├── pages/               # Page components
│   ├── hooks/               # Custom React hooks
│   │   ├── useOfflineSync.ts    # Offline sync logic
│   │   ├── useLeads.ts          # Leads data hook
│   │   └── ...
│   ├── services/            # API & database services
│   │   ├── api.ts           # Axios instance
│   │   ├── db.ts            # Dexie database
│   │   └── sync.ts          # Sync logic
│   ├── types/               # TypeScript types
│   ├── styles/              # Global styles
│   │   └── globals.css      # Tailwind CSS imports
│   ├── App.tsx              # Root component
│   └── main.tsx             # Entry point
├── public/
│   ├── service-worker.js    # Service worker for offline
│   └── ...
├── vite.config.ts           # Vite configuration
├── tailwind.config.ts       # Tailwind configuration
├── package.json             # Dependencies
└── tsconfig.json            # TypeScript configuration
```

## Available Scripts

```bash
# Development
npm run dev          # Start dev server with HMR

# Production
npm run build        # Build for production
npm run preview      # Preview production build locally

# Linting
npm run lint         # Run ESLint
npm run lint:fix     # Fix linting issues

# Type checking
npm run type-check   # Run TypeScript compiler
```

## Building for Production

```bash
npm run build
```

This creates an optimized production build in the `dist/` folder.

## Offline Functionality

The app uses **IndexedDB** for local data storage and **Service Workers** for offline support:

1. **First Load**: Fetches data from API and caches it locally
2. **Offline Mode**: Uses cached data when internet is unavailable
3. **Sync Queue**: All changes (add/edit/delete) are queued locally
4. **Auto Sync**: When internet returns, automatically syncs queued changes
5. **Conflict Resolution**: Server version takes precedence on conflicts

### Offline Actions Supported

- Add new leads
- Edit lead information
- Delete leads
- Update custom fields
- Add notes/activities
- Change lead status/category

## API Integration

The frontend communicates with the Django REST API. Key endpoints:

```
POST   /api/auth/login/          - User login
GET    /api/auth/user/           - Current user
GET    /api/leads/               - List leads
POST   /api/leads/               - Create lead
GET    /api/leads/{id}/          - Get lead
PUT    /api/leads/{id}/          - Update lead
DELETE /api/leads/{id}/          - Delete lead
GET    /api/categories/          - List categories
GET    /api/sources/             - List sources
```

## Design System

### Colors
- **Primary**: #8b640d (Brown)
- **Secondary**: #092C4C (Dark Blue)
- **Accent**: #F39C12 (Gold)
- **Background**: #F5F5F5 (Light Gray)
- **Text**: #333333 (Dark Gray)

### Typography
- **Headings**: Poppins (Bold)
- **Body**: Nunito (Regular)

### Spacing & Layout
- Uses Tailwind's spacing scale (4px base unit)
- Flexbox for most layouts
- CSS Grid for complex 2D layouts

## Deployment

### Vercel (Recommended)

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
vercel
```

### Other Platforms

#### Netlify
```bash
npm run build
# Deploy dist/ folder to Netlify
```

#### Docker
Create a `Dockerfile`:

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "run", "preview"]
```

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API URL | `http://localhost:8000/api` |
| `VITE_APP_NAME` | Application name | `LeadSync CRM` |

## Troubleshooting

### API Connection Errors
- Ensure backend is running
- Check `VITE_API_URL` in `.env`
- Verify CORS settings in backend

### Data Not Syncing
- Check browser console for errors
- Verify internet connection
- Clear browser cache and reload

### Build Errors
- Delete `node_modules/` and `package-lock.json`
- Run `npm install` again
- Run `npm run build`

### Service Worker Issues
- Clear browser cache
- Unregister old service workers in DevTools
- Hard refresh (Ctrl+Shift+R or Cmd+Shift+R)

## Performance Tips

1. **Code Splitting**: Routes are automatically code-split by Vite
2. **Image Optimization**: Use Vite's image import optimization
3. **Caching**: React Query caches API responses automatically
4. **Service Worker**: Enables offline support and faster loads

## Contributing

Follow the project structure and coding conventions:

- Use TypeScript for type safety
- Follow Tailwind CSS conventions for styling
- Keep components small and focused
- Write custom hooks for reusable logic
- Test offline scenarios

## Support

For issues or questions, please contact the development team.
