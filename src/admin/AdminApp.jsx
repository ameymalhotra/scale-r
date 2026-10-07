import React, { useLayoutEffect } from 'react';
import { Route, Routes } from 'react-router-dom';
import { AdminAuthProvider, RequireAdmin } from './auth.jsx';
import { DraftProvider } from './draftStore.jsx';
import AdminLayout from './AdminLayout.jsx';
import DataPage from './DataPage.jsx';
import { FiltersProvider } from './filtersStore.jsx';
import LiveToolPage from './LiveToolPage.jsx';
import LoginPage from './LoginPage.jsx';
import VersionsPage from './VersionsPage.jsx';
import './admin.css';

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
          path="*"
          element={
            <RequireAdmin>
              <DraftProvider>
                <FiltersProvider>
                  <AdminLayout>
                    <Routes>
                      <Route index element={<DataPage />} />
                      <Route path="versions" element={<VersionsPage />} />
                      <Route path="live-tool" element={<LiveToolPage />} />
                    </Routes>
                  </AdminLayout>
                </FiltersProvider>
              </DraftProvider>
            </RequireAdmin>
          }
        />
      </Routes>
    </AdminAuthProvider>
  );
}
