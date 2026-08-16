import React, { useLayoutEffect, useEffect, Suspense, lazy } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import Navbar from './components/Navbar.jsx';
import About from './pages/About.jsx';
import Dashboard from './pages/Dashboard.jsx';

// About and Dashboard stay eagerly imported on purpose. About is the landing
// route ("/" redirects to it), so deferring it would put a chunk request in
// front of first paint; Dashboard owns its own in-place loading indicator,
// which a Suspense fallback cannot reproduce without changing what the user
// sees while it loads. The secondary pages below are never the first paint of
// a measured route, so splitting them is free.
const Team = lazy(() => import('./pages/Team.jsx'));
const Partners = lazy(() => import('./pages/Partners.jsx'));
const TechnicalDocs = lazy(() => import('./pages/TechnicalDocs.jsx'));
const Outputs = lazy(() => import('./pages/Outputs.jsx'));

const ROUTE_TITLES = {
  '/about': 'About the project',
  '/dashboard': 'Dashboard',
  '/team': 'Team',
  '/partners': 'Partners',
  '/docs': 'Technical documentation',
  '/outputs': 'Outputs',
};

const BASE_TITLE = 'Miami-Dade Climate Resilience';

export default function App() {
  const location = useLocation();

  useLayoutEffect(() => {
    document.documentElement.classList.toggle(
      'route-dashboard',
      location.pathname.startsWith('/dashboard'),
    );
  }, [location.pathname]);

  useEffect(() => {
    const path = location.pathname;
    const page = ROUTE_TITLES[path] || ROUTE_TITLES['/about'];
    document.title = `${page} | ${BASE_TITLE}`;
  }, [location.pathname]);

  return (
    <div className="app-shell">
      <a href="#main" className="skip-to-content">
        Skip to main content
      </a>
      <Navbar />

      <main id="main" className="app-main-scroll" tabIndex={-1}>
        <Suspense fallback={null}>
          <Routes>
            <Route path="/" element={<Navigate to="/about" replace />} />
            <Route path="/about" element={<About />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/team" element={<Team />} />
            <Route path="/partners" element={<Partners />} />
            <Route path="/docs" element={<TechnicalDocs />} />
            <Route path="/outputs" element={<Outputs />} />
          </Routes>
        </Suspense>
      </main>
    </div>
  );
}
