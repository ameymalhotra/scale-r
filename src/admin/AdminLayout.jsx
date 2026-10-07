import React, { useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import { useAdminAuth, useDraft } from './contexts.js';

const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;

function DraftStatus() {
  const { load, busy, unsavedCount, unpublishedCount, currentVersion } = useDraft();

  if (load.status === 'loading') return <span className="admin-muted">Loading data…</span>;
  if (load.status === 'error') return <span className="admin-error">Could not load data: {load.error}</span>;

  const since = currentVersion ? `since version ${currentVersion.version_no}` : 'not yet published';
  return (
    <span className="admin-status" aria-live="polite">
      {busy && <span className="admin-status__busy">{busy.charAt(0).toUpperCase() + busy.slice(1)}…</span>}
      <span className={unsavedCount ? 'admin-pill admin-pill--warn' : 'admin-pill'}>
        {unsavedCount ? `${plural(unsavedCount, 'unsaved change')}` : 'All changes saved'}
      </span>
      <span className={unpublishedCount ? 'admin-pill admin-pill--info' : 'admin-pill'}>
        {unpublishedCount
          ? `${plural(unpublishedCount, 'saved row change')} not published (${since})`
          : `Draft matches the live map${currentVersion ? ` (version ${currentVersion.version_no})` : ''}`}
      </span>
    </span>
  );
}

export default function AdminLayout({ children }) {
  const { email, signOut } = useAdminAuth();
  const { unsavedCount } = useDraft();

  useEffect(() => {
    if (!unsavedCount) return undefined;
    const warn = (event) => {
      event.preventDefault();
      event.returnValue = '';
    };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [unsavedCount]);

  return (
    <div className="admin-shell">
      <aside className="admin-sidebar" aria-label="Admin sections">
        <div className="admin-brand">SCALE-R admin</div>
        <nav className="admin-nav">
          <NavLink to="/admin" end className={({ isActive }) => `admin-nav__link${isActive ? ' is-active' : ''}`}>
            Project data
          </NavLink>
          <NavLink
            to="/admin/versions"
            className={({ isActive }) => `admin-nav__link${isActive ? ' is-active' : ''}`}
          >
            Versions
          </NavLink>
          <NavLink
            to="/admin/live-tool"
            className={({ isActive }) => `admin-nav__link${isActive ? ' is-active' : ''}`}
          >
            Live tool
          </NavLink>
          <a className="admin-nav__link" href="/dashboard" target="_blank" rel="noreferrer">
            Open public map ↗
          </a>
        </nav>
        <div className="admin-sidebar__footer">
          <span className="admin-muted" title={email}>
            {email}
          </span>
          <button type="button" className="admin-btn admin-btn--small" onClick={signOut}>
            Sign out
          </button>
        </div>
      </aside>
      <div className="admin-main">
        <header className="admin-topbar">
          <DraftStatus />
        </header>
        <div className="admin-content">{children}</div>
      </div>
    </div>
  );
}
