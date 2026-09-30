import React, { useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAdminAuth } from './contexts.js';

export default function LoginPage() {
  const { client, status } = useAdminAuth();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(null);

  if (status === 'admin' || status === 'forbidden') {
    return <Navigate to={location.state?.from || '/admin'} replace />;
  }

  const signInWithPassword = async (event) => {
    event.preventDefault();
    setBusy(true);
    setMessage(null);
    const { error } = await client.auth.signInWithPassword({ email: email.trim(), password });
    setBusy(false);
    if (error) setMessage({ kind: 'error', text: error.message });
  };

  const sendMagicLink = async () => {
    if (!email.trim()) {
      setMessage({ kind: 'error', text: 'Enter your email first.' });
      return;
    }
    setBusy(true);
    setMessage(null);
    const { error } = await client.auth.signInWithOtp({
      email: email.trim(),
      options: { shouldCreateUser: false, emailRedirectTo: `${window.location.origin}/admin` },
    });
    setBusy(false);
    setMessage(
      error
        ? { kind: 'error', text: error.message }
        : { kind: 'info', text: `Check ${email.trim()} for a sign-in link.` },
    );
  };

  return (
    <div className="admin-center">
      <form className="admin-login" onSubmit={signInWithPassword}>
        <h1 className="admin-title">SCALE-R data admin</h1>
        <p className="admin-muted">Sign in to manage the projects shown on the public map.</p>

        <label className="admin-field">
          <span>Email</span>
          <input
            type="email"
            autoComplete="username"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>
        <label className="admin-field">
          <span>Password</span>
          <input
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>

        {message && (
          <p className={message.kind === 'error' ? 'admin-error' : 'admin-info'} role="alert">
            {message.text}
          </p>
        )}

        <button type="submit" className="admin-btn admin-btn--primary" disabled={busy || !password}>
          Sign in
        </button>
        <button type="button" className="admin-btn admin-btn--link" onClick={sendMagicLink} disabled={busy}>
          Email me a sign-in link instead
        </button>
      </form>
    </div>
  );
}
