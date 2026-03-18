import React from 'react';
import { NavLink } from 'react-router-dom';

const navLinks = [
  { to: '/about', label: 'About the project' },
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/team', label: 'Team' },
  { to: '/partners', label: 'Partners' },
  { to: '/docs', label: 'Technical Documentation' },
  { to: '/outputs', label: 'Outputs' },
];

const navStyle = {
  background: 'rgba(1, 50, 30, 0.95)',
  borderBottom: '1px solid rgba(255, 255, 255, 0.15)',
  padding: '0 24px',
  display: 'flex',
  flexWrap: 'wrap',
  gap: 0,
  alignItems: 'center',
  flexShrink: 0,
};

const linkBase = {
  display: 'block',
  padding: '12px 16px',
  color: 'rgba(255, 255, 255, 0.85)',
  textDecoration: 'none',
  fontSize: '0.9rem',
  fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
  fontWeight: 400,
  transition: 'color 0.2s ease, background 0.2s ease',
};

export default function Navbar() {
  return (
    <nav style={navStyle} className="site-navbar" role="navigation">
      {navLinks.map(({ to, label }) => (
        <NavLink
          key={to}
          to={to}
          style={({ isActive }) => ({
            ...linkBase,
            ...(isActive
              ? { color: '#fff', background: 'rgba(255, 255, 255, 0.15)', fontWeight: 500 }
              : {}),
          })}
          end={to === '/about'}
        >
          {label}
        </NavLink>
      ))}
    </nav>
  );
}
