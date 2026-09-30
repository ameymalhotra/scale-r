import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { supabase } from '../lib/supabaseClient.js';
import { AdminAuthContext, useAdminAuth } from './contexts.js';

/**
 * status:
 *   'loading'      session or admin check in flight
 *   'signed-out'   no session
 *   'forbidden'    signed in, but email is not in admin_users
 *   'admin'        signed in and allowlisted
 *   'unconfigured' VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY missing
 */
export function AdminAuthProvider({ client = supabase, children }) {
  const [session, setSession] = useState(null);
  const [status, setStatus] = useState(client ? 'loading' : 'unconfigured');

  const checkAdmin = useCallback(
    async (nextSession) => {
      setSession(nextSession);
      if (!nextSession) {
        setStatus('signed-out');
        return;
      }
      setStatus('loading');
      const { data, error } = await client.rpc('is_admin');
      setStatus(!error && data === true ? 'admin' : 'forbidden');
    },
    [client],
  );

  useEffect(() => {
    if (!client) return undefined;
    let active = true;
    client.auth.getSession().then(({ data }) => {
      if (active) checkAdmin(data.session);
    });
    const { data: listener } = client.auth.onAuthStateChange((event, nextSession) => {
      if (!active || event === 'INITIAL_SESSION' || event === 'TOKEN_REFRESHED') return;
      checkAdmin(nextSession);
    });
    return () => {
      active = false;
      listener.subscription.unsubscribe();
    };
  }, [client, checkAdmin]);

  const signOut = useCallback(async () => {
    if (client) await client.auth.signOut();
  }, [client]);

  const value = useMemo(
    () => ({
      client,
      session,
      status,
      email: session?.user?.email ?? '',
      signOut,
    }),
    [client, session, status, signOut],
  );

  return <AdminAuthContext.Provider value={value}>{children}</AdminAuthContext.Provider>;
}

export function RequireAdmin({ children }) {
  const { status, email, signOut } = useAdminAuth();
  const location = useLocation();

  if (status === 'loading') {
    return (
      <div className="admin-center" role="status">
        Checking your access…
      </div>
    );
  }
  if (status === 'unconfigured') {
    return (
      <div className="admin-center">
        <p>
          The admin dashboard needs <code>VITE_SUPABASE_URL</code> and <code>VITE_SUPABASE_ANON_KEY</code> to be set.
        </p>
      </div>
    );
  }
  if (status === 'signed-out') {
    return <Navigate to="/admin/login" replace state={{ from: location.pathname }} />;
  }
  if (status === 'forbidden') {
    return (
      <div className="admin-center">
        <h1 className="admin-title">No admin access</h1>
        <p>
          {email} is signed in but is not on the admin allowlist. Ask a project admin to add this email to{' '}
          <code>admin_users</code>.
        </p>
        <button type="button" className="admin-btn" onClick={signOut}>
          Sign out
        </button>
      </div>
    );
  }
  return children;
}
