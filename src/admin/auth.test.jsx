import React from 'react';
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { AdminAuthProvider, RequireAdmin } from './auth.jsx';

function fakeClient({ session = null, isAdmin = false } = {}) {
  return {
    auth: {
      getSession: vi.fn().mockResolvedValue({ data: { session } }),
      onAuthStateChange: vi.fn(() => ({ data: { subscription: { unsubscribe: vi.fn() } } })),
      signOut: vi.fn().mockResolvedValue({}),
    },
    rpc: vi.fn().mockResolvedValue({ data: isAdmin, error: null }),
  };
}

function renderGuarded(client) {
  return render(
    <MemoryRouter initialEntries={['/admin']}>
      <AdminAuthProvider client={client}>
        <Routes>
          <Route path="/admin/login" element={<p>Login page</p>} />
          <Route
            path="/admin"
            element={
              <RequireAdmin>
                <p>Secret table</p>
              </RequireAdmin>
            }
          />
        </Routes>
      </AdminAuthProvider>
    </MemoryRouter>,
  );
}

const session = { user: { email: 'prof@miami.edu' } };

describe('RequireAdmin', () => {
  it('sends signed-out visitors to the login page', async () => {
    renderGuarded(fakeClient());
    expect(await screen.findByText('Login page')).toBeInTheDocument();
    expect(screen.queryByText('Secret table')).not.toBeInTheDocument();
  });

  it('shows the admin area to allowlisted users', async () => {
    const client = fakeClient({ session, isAdmin: true });
    renderGuarded(client);
    expect(await screen.findByText('Secret table')).toBeInTheDocument();
    expect(client.rpc).toHaveBeenCalledWith('is_admin');
  });

  it('blocks signed-in users who are not on the allowlist', async () => {
    renderGuarded(fakeClient({ session, isAdmin: false }));
    expect(await screen.findByText('No admin access')).toBeInTheDocument();
    expect(screen.getByText(/prof@miami.edu is signed in/)).toBeInTheDocument();
    expect(screen.queryByText('Secret table')).not.toBeInTheDocument();
  });

  it('explains missing configuration instead of crashing', () => {
    renderGuarded(null);
    expect(screen.getByText(/needs/)).toBeInTheDocument();
  });
});
