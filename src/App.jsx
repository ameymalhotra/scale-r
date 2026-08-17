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

const ROUTE_META = {
  '/about': {
    title: 'About the project',
    description:
      'SCALE-R is an NSF-funded University of Miami initiative that maps coastal adaptation interventions and models disaster risk reduction across Miami-Dade County.',
  },
  '/dashboard': {
    title: 'Dashboard',
    description:
      'Explore SCALE-R’s interactive map of climate resilience projects, infrastructure types, and disaster-risk layers across Miami-Dade County.',
  },
  '/team': {
    title: 'Team',
    description:
      'Meet the University of Miami researchers and students building SCALE-R, an NSF-funded coastal resilience decision-support project for Miami-Dade County.',
  },
  '/partners': {
    title: 'Partners',
    description:
      'Academic, government, and community partners collaborating on SCALE-R to advance coastal adaptation in Miami-Dade County.',
  },
  '/docs': {
    title: 'Technical documentation',
    description:
      'Data sources, infrastructure types, disaster-focus layers, and modeling methods behind the SCALE-R Miami-Dade climate resilience dashboard.',
  },
  '/outputs': {
    title: 'Outputs',
    description:
      'Research products, datasets, and program deliverables from the SCALE-R coastal resilience project at the University of Miami.',
  },
};

const BASE_TITLE = 'Miami-Dade Climate Resilience';
const DEFAULT_META = ROUTE_META['/about'];

function setMetaDescription(text) {
  let el = document.querySelector('meta[name="description"]');
  if (!el) {
    el = document.createElement('meta');
    el.setAttribute('name', 'description');
    document.head.appendChild(el);
  }
  el.setAttribute('content', text);
}

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
    const meta = ROUTE_META[path] || DEFAULT_META;
    document.title = `${meta.title} | ${BASE_TITLE}`;
    setMetaDescription(meta.description);
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
