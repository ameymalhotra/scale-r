import React from 'react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

// The Scenario view (prompt 22) is admin only (DECISIONS.md D-094). These tests drive the real
// AdminApp routes with a fake Supabase client, so they check the guard the site actually uses.
const state = { session: null, isAdmin: false };
vi.mock('../../lib/supabaseClient.js', () => ({
  supabase: {
    auth: {
      getSession: vi.fn(() => Promise.resolve({ data: { session: state.session } })),
      onAuthStateChange: vi.fn(() => ({ data: { subscription: { unsubscribe: vi.fn() } } })),
      signOut: vi.fn(() => Promise.resolve({})),
    },
    rpc: vi.fn(() => Promise.resolve({ data: state.isAdmin, error: null })),
  },
}));
// The map itself needs WebGL; stand in for the view so only routing and the guard are tested.
vi.mock('./VizPage.jsx', () => ({ default: ({ view }) => <p>Viz view: {view}</p> }));

const { default: AdminApp } = await import('../AdminApp.jsx');

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/admin/*" element={<AdminApp />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('admin Scenario view', () => {
  beforeEach(() => {
    state.session = null;
    state.isAdmin = false;
  });

  it('sends a signed-out visitor to the admin login, without rendering the view', async () => {
    renderAt('/admin/viz/scenario');
    expect(await screen.findByRole('button', { name: 'Sign in' })).toBeInTheDocument();
    expect(screen.queryByText(/Viz view/)).not.toBeInTheDocument();
  });

  it('blocks a signed-in user who is not an admin', async () => {
    state.session = { user: { email: 'someone@example.com' } };
    renderAt('/admin/viz/scenario');
    expect(await screen.findByText('No admin access')).toBeInTheDocument();
    expect(screen.queryByText(/Viz view/)).not.toBeInTheDocument();
  });

  it('shows the Scenario view to an admin', async () => {
    state.session = { user: { email: 'prof@miami.edu' } };
    state.isAdmin = true;
    renderAt('/admin/viz/scenario');
    expect(await screen.findByText('Viz view: scenario')).toBeInTheDocument();
  });
});
