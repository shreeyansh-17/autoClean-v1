# AutoClean Frontend

React + Vite frontend for the AutoClean project.

## Getting Started

```bash
cd frontend
npm install
npm run dev
```

## Available Scripts

| Script | Description |
|--------|-------------|
| `npm run dev` | Start the Vite dev server on http://localhost:5173 |
| `npm run build` | Build for production into `dist/` |
| `npm run preview` | Preview the production build locally |
| `npm run lint` | Run ESLint |

## Folder Structure

```
src/
├── assets/        # Static assets (images, icons, fonts)
├── components/    # Reusable UI components (Navbar, Footer, …)
├── hooks/         # Custom React hooks
├── layouts/       # Page layout wrappers (MainLayout)
├── pages/         # Route-level page components
├── services/      # API service functions (api.js)
└── styles/        # Global CSS files
```

## Environment Variables

Create a `.env.local` file in the `frontend/` directory:

```env
VITE_API_URL=http://localhost:8000
```

> **Note:** Backend integration is not yet wired up. The `src/services/api.js` file contains stub functions ready to be connected when the Python backend is available.

