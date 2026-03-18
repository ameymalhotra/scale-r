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
  padding: '10px 30px',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
  flexShrink: 0,
  fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
};

export default function App() {
  const [showTooltip, setShowTooltip] = useState(false);

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
              fontSize: '2em',
              margin: 0,
              fontWeight: 300,
              letterSpacing: '0.5px',
              cursor: 'pointer',
              transition: 'color 0.2s ease',
              color: showTooltip ? '#60a5fa' : 'white',
            }}
            onMouseEnter={() => setShowTooltip(true)}
            onMouseLeave={() => setShowTooltip(false)}
          >
            SCALE-R Resilience Dashboard
          </h1>
          <p
            style={{
              fontSize: '0.9em',
              margin: '3px 0 0 0',
              opacity: 0.8,
              fontWeight: 300,
            }}
          >
            Comprehensive mapping of adaptation strategies, projects, and investments in Miami-Dade County
          </p>
          {showTooltip && (
            <div
              style={{
                position: 'absolute',
                left: 0,
                top: '100%',
                marginTop: '8px',
                width: '384px',
                backgroundColor: 'rgba(255, 255, 255, 0.8)',
                backdropFilter: 'blur(20px) saturate(180%)',
                WebkitBackdropFilter: 'blur(20px) saturate(180%)',
                borderRadius: '12px',
                boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.15), 0 10px 10px -5px rgba(0, 0, 0, 0.08), inset 0 0 0 1px rgba(255, 255, 255, 0.6)',
                border: '1px solid rgba(255, 255, 255, 0.3)',
                overflow: 'hidden',
                zIndex: 1000,
                padding: '20px',
              }}
            >
              <p style={{ fontSize: '0.875rem', color: '#4b5563', lineHeight: '1.75', margin: '0 0 16px 0' }}>
                A comprehensive dashboard for visualizing climate resilience projects across Miami-Dade County, featuring interactive maps, project filtering, and community risk assessments.
              </p>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', paddingTop: '12px', borderTop: '1px solid #f3f4f6' }}>
                <div>
                  <p style={{ fontSize: '0.75rem', color: '#9ca3af', margin: '0 0 2px 0' }}>Location</p>
                  <p style={{ fontSize: '0.75rem', fontWeight: 500, color: '#374151', margin: 0 }}>Miami-Dade</p>
                </div>
                <div>
                  <p style={{ fontSize: '0.75rem', color: '#9ca3af', margin: '0 0 2px 0' }}>Updated</p>
                  <p style={{ fontSize: '0.75rem', fontWeight: 500, color: '#374151', margin: 0 }}>2025</p>
                </div>
              </div>
            </div>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '30px', flexShrink: 0 }}>
          <img src="/Images/1019px-NSF_logo.png" alt="NSF Logo" style={{ height: '75px', width: 'auto' }} />
          <img src="/Images/Miami_Hurricanes_logo.svg.png" alt="Miami Hurricanes Logo" style={{ height: '50px', width: 'auto' }} />
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
