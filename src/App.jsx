import React, { useLayoutEffect } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import Navbar from './components/Navbar.jsx';
import About from './pages/About.jsx';
import Dashboard from './pages/Dashboard.jsx';
import Team from './pages/Team.jsx';
import Partners from './pages/Partners.jsx';
import TechnicalDocs from './pages/TechnicalDocs.jsx';
import Outputs from './pages/Outputs.jsx';

export default function App() {
  const location = useLocation();

  useLayoutEffect(() => {
    document.documentElement.classList.toggle(
      'route-dashboard',
      location.pathname.startsWith('/dashboard'),
    );
  }, [location.pathname]);

  return (
    <div className="app-shell">
      <Navbar />

      <main className="app-main-scroll">
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
