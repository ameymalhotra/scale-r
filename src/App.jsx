import React, { useLayoutEffect, useEffect } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import Navbar from './components/Navbar.jsx';
import About from './pages/About.jsx';
import Dashboard from './pages/Dashboard.jsx';
import Team from './pages/Team.jsx';
import Partners from './pages/Partners.jsx';
import TechnicalDocs from './pages/TechnicalDocs.jsx';
import Outputs from './pages/Outputs.jsx';

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
        <Routes>
          <Route path="/" element={<Navigate to="/about" replace />} />
          <Route path="/about" element={<About />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/team" element={<Team />} />
          <Route path="/partners" element={<Partners />} />
          <Route path="/docs" element={<TechnicalDocs />} />
          <Route path="/outputs" element={<Outputs />} />
        </Routes>
      </main>
    </div>
  );
}
