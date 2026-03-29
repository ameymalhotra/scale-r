import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar.jsx';
import About from './pages/About.jsx';
import Dashboard from './pages/Dashboard.jsx';
import Team from './pages/Team.jsx';
import Partners from './pages/Partners.jsx';
import TechnicalDocs from './pages/TechnicalDocs.jsx';
import Outputs from './pages/Outputs.jsx';

export default function App() {
  return (
    <div
      style={{
        margin: 0,
        padding: 0,
        fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
        backgroundColor: 'white',
        height: '100%',
        width: '100%',
        overflow: 'hidden',
        boxSizing: 'border-box',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <Navbar />

      <main
        style={{
          flex: 1,
          minHeight: 0,
          overflow: 'auto',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
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
