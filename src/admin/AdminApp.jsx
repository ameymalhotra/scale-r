import React, { Suspense, lazy, useLayoutEffect } from 'react';
import { Route, Routes } from 'react-router-dom';
import { AdminAuthProvider, RequireAdmin } from './auth.jsx';
import { DraftProvider } from './draftStore.jsx';
import AdminLayout from './AdminLayout.jsx';
import DataPage from './DataPage.jsx';
import { FiltersProvider } from './filtersStore.jsx';
import LayersPage from './LayersPage.jsx';
import { LayersProvider } from './layersStore.jsx';
import LiveToolPage from './LiveToolPage.jsx';
import LoginPage from './LoginPage.jsx';
import VersionsPage from './VersionsPage.jsx';
import './admin.css';

// Mapbox and the draft data load only when an admin opens a visualization.
const VizPage = lazy(() => import('./viz/VizPage.jsx'));

export default function AdminApp() {
  useLayoutEffect(() => {
    document.documentElement.classList.add('route-admin');
    return () => document.documentElement.classList.remove('route-admin');
  }, []);

  return (
    <AdminAuthProvider>
      <Routes>
        <Route path="login" element={<LoginPage />} />
        <Route
          path="viz/*"
          element={
            <RequireAdmin>
              <Suspense fallback={<div className="admin-center" role="status">Loading map…</div>}>
                <Routes>
                  <Route index element={<VizPage view="gap" />} />
                  <Route path="exposure" element={<VizPage view="exposure" />} />
                </Routes>
              </Suspense>
            </RequireAdmin>
          }
        />
        <Route
          path="*"
          element={
            <RequireAdmin>
              <DraftProvider>
                <FiltersProvider>
                  <LayersProvider>
                    <AdminLayout>
                      <Routes>
                        <Route index element={<DataPage />} />
                        <Route path="versions" element={<VersionsPage />} />
                        <Route path="live-tool" element={<LiveToolPage />} />
                        <Route path="layers" element={<LayersPage />} />
                      </Routes>
                    </AdminLayout>
                  </LayersProvider>
                </FiltersProvider>
              </DraftProvider>
            </RequireAdmin>
          }
        />
      </Routes>
    </AdminAuthProvider>
  );
}
