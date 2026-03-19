import React, { useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar.jsx';
import About from './pages/About.jsx';
import Dashboard from './pages/Dashboard.jsx';
import Team from './pages/Team.jsx';
import Partners from './pages/Partners.jsx';
import TechnicalDocs from './pages/TechnicalDocs.jsx';
import Outputs from './pages/Outputs.jsx';

const headerStyle = {
  background: '#01321e',
  color: 'white',
  padding: '6px 20px',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
  flexShrink: 0,
  fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
};

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
      <header style={headerStyle}>
        <div style={{ position: 'relative', minWidth: 0 }}>
          <h1
            style={{
              fontSize: '1.6em',
              margin: 0,
              fontWeight: 300,
              letterSpacing: '0.5px',
              cursor: 'pointer',
              transition: 'color 0.2s ease',
              color: 'white',
            }}
          >
            SCALE-R Resilience Dashboard
          </h1>
          <p
            style={{
              fontSize: '0.8em',
              margin: '3px 0 0 0',
              opacity: 0.8,
              fontWeight: 300,
            }}
          >
            Comprehensive mapping of adaptation strategies, projects, and investments in Miami-Dade County
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '30px', flexShrink: 0 }}>
          <img src="/Images/1019px-NSF_logo.png" alt="NSF Logo" style={{ height: '60px', width: 'auto' }} />
          <img src="/Images/Miami_Hurricanes_logo.svg.png" alt="Miami Hurricanes Logo" style={{ height: '40px', width: 'auto' }} />
        </div>
      </header>

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
