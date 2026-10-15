import { createContext, useContext } from 'react';

export const AdminAuthContext = createContext(null);
export const DraftContext = createContext(null);
export const FiltersContext = createContext(null);
export const LayersContext = createContext(null);

export const isNewRowId = (id) => typeof id === 'string' && id.startsWith('new-');

export function useAdminAuth() {
  const ctx = useContext(AdminAuthContext);
  if (!ctx) throw new Error('useAdminAuth must be used inside AdminAuthProvider');
  return ctx;
}

export function useDraft() {
  const ctx = useContext(DraftContext);
  if (!ctx) throw new Error('useDraft must be used inside DraftProvider');
  return ctx;
}

export function useFilters() {
  const ctx = useContext(FiltersContext);
  if (!ctx) throw new Error('useFilters must be used inside FiltersProvider');
  return ctx;
}

export function useLayers() {
  const ctx = useContext(LayersContext);
  if (!ctx) throw new Error('useLayers must be used inside LayersProvider');
  return ctx;
}
