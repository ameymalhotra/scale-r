import React from 'react';
import { NavLink } from 'react-router-dom';

const navLinks = [
  { to: '/about', label: 'About the project' },
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/team', label: 'Team' },
  { to: '/docs', label: 'Technical documentation' },
];

export default function Navbar() {
  return (
    <nav className="site-navbar" role="navigation" aria-label="Main">
      {navLinks.map(({ to, label }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            `site-navbar-link${isActive ? ' site-navbar-link--active' : ''}`
          }
          end={to === '/about'}
        >
          {label}
        </NavLink>
      ))}
    </nav>
  );
}
