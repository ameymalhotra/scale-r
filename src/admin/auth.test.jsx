import React from 'react';
import { describe, expect, it, vi } from 'vitest';
import { act, render, screen } from '@testing-library/react';
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

// Supabase reports SIGNED_IN again for the same user each time the tab becomes visible (D-221).
describe('returning to the tab', () => {
  const admin = { user: { id: 'u1', email: 'prof@miami.edu' } };

  function setup() {
    let emit;
    const client = fakeClient({ session: admin, isAdmin: true });
    client.auth.onAuthStateChange = vi.fn((cb) => { emit = cb; return { data: { subscription: { unsubscribe: vi.fn() } } }; });
    let mounts = 0;
    function Page() {
      React.useEffect(() => { mounts += 1; }, []);
      return <p>Secret table</p>;
    }
    render(
      <MemoryRouter initialEntries={['/admin']}>
        <AdminAuthProvider client={client}>
          <Routes>
            <Route path="/admin" element={<RequireAdmin><Page /></RequireAdmin>} />
          </Routes>
        </AdminAuthProvider>
      </MemoryRouter>,
    );
    return { client, emit: (...a) => emit(...a), mounts: () => mounts };
  }

  it('keeps the page as it is for the same admin', async () => {
    const t = setup();
    expect(await screen.findByText('Secret table')).toBeTruthy();
    expect(t.mounts()).toBe(1);
    await act(async () => { t.emit('SIGNED_IN', { ...admin }); });
    expect(screen.queryByText(/Checking your access/)).toBeNull();
    expect(screen.getByText('Secret table')).toBeTruthy();
    expect(t.mounts()).toBe(1);
    expect(t.client.rpc).toHaveBeenCalledTimes(1);
  });

  it('checks a different user again', async () => {
    const t = setup();
    await screen.findByText('Secret table');
    t.client.rpc.mockResolvedValueOnce({ data: false, error: null });
    await act(async () => { t.emit('SIGNED_IN', { user: { id: 'u2', email: 'other@example.com' } }); });
    expect(await screen.findByText('No admin access')).toBeTruthy();
    expect(t.client.rpc).toHaveBeenCalledTimes(2);
  });
});
