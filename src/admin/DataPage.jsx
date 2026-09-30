import React, { useCallback, useMemo, useState } from 'react';
import DataTable from './DataTable.jsx';
import PublishDialog from './PublishDialog.jsx';
import RowEditor from './RowEditor.jsx';
import { downloadCsv } from './csv.js';
import { isNewRowId, useDraft } from './contexts.js';

const VIEWS = [
  { id: 'all', label: 'All rows' },
  { id: 'changed', label: 'Unsaved changes' },
  { id: 'errors', label: 'Rows with errors' },
  { id: 'warnings', label: 'Rows with warnings' },
];

export default function DataPage() {
  const draft = useDraft();
  const {
    load,
    busy,
    rows,
    validation,
    unsavedCount,
    unpublishedCount,
    rowState,
    editedFields,
    updateCell,
    addRow,
    setAutoProjectId,
    deleteRows,
    restoreRows,
    revertRow,
    discard,
    save,
  } = draft;

  const [view, setView] = useState('all');
  const [globalFilter, setGlobalFilter] = useState('');
  const [columnFilters, setColumnFilters] = useState([]);
  const [sorting, setSorting] = useState([]);
  const [selectedIds, setSelectedIds] = useState(() => new Set());
  const [openRowId, setOpenRowId] = useState(null);
  const [publishOpen, setPublishOpen] = useState(false);
  const [notice, setNotice] = useState(null);

  const viewRows = useMemo(() => {
    if (view === 'changed') return rows.filter((r) => rowState(r.id));
    if (view === 'errors') {
      return rows.filter((r) => Object.keys(validation.byId.get(r.id)?.errors ?? {}).length);
    }
    if (view === 'warnings') {
      return rows.filter((r) => Object.keys(validation.byId.get(r.id)?.warnings ?? {}).length);
    }
    return rows;
  }, [rows, view, rowState, validation]);

  const toggleSelect = useCallback((id) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const toggleSelectAll = useCallback((ids, select) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      for (const id of ids) {
        if (select) next.add(id);
        else next.delete(id);
      }
      return next;
    });
  }, []);

  const handleAdd = () => {
    const id = addRow();
    setView('all');
    setSorting([]);
    setGlobalFilter('');
    setColumnFilters([]);
    setOpenRowId(id);
  };

  const selectedList = [...selectedIds];
  const selectedDeletable = selectedList.filter((id) => rowState(id) !== 'deleted');
  const selectedDeleted = selectedList.filter((id) => rowState(id) === 'deleted');

  const handleDeleteSelected = () => {
    deleteRows(selectedDeletable);
    setSelectedIds(new Set());
  };

  const handleSave = async () => {
    setNotice(null);
    const result = await save();
    if (result.ok) {
      setSelectedIds(new Set());
      setNotice({
        kind: result.tractWarning ? 'warning' : 'info',
        text: result.tractWarning || 'Draft saved. Nothing changes on the public map until you publish.',
      });
    } else {
      setNotice({ kind: 'error', text: result.error });
      if (result.error.includes('errors')) setView('errors');
    }
  };

  const handleDiscard = () => {
    if (!window.confirm(`Discard ${unsavedCount} unsaved change${unsavedCount === 1 ? '' : 's'}?`)) return;
    discard();
    setOpenRowId(null);
    setNotice(null);
  };

  if (load.status === 'loading') return <p className="admin-center">Loading project data…</p>;
  if (load.status === 'error' && rows.length === 0) {
    return (
      <div className="admin-center">
        <p className="admin-error">Could not load project data: {load.error}</p>
        <button type="button" className="admin-btn" onClick={draft.reload}>
          Try again
        </button>
      </div>
    );
  }

  const openRow = openRowId != null ? rows.find((r) => r.id === openRowId) : null;

  return (
    <div className="admin-page">
      <div className="admin-toolbar" role="toolbar" aria-label="Table actions">
        <input
          type="search"
          className="admin-search"
          placeholder="Search all fields…"
          aria-label="Search all fields"
          value={globalFilter}
          onChange={(e) => setGlobalFilter(e.target.value)}
        />
        <select className="admin-select" aria-label="Show" value={view} onChange={(e) => setView(e.target.value)}>
          {VIEWS.map((v) => (
            <option key={v.id} value={v.id}>
              {v.label}
              {v.id === 'errors' && validation.errorRows ? ` (${validation.errorRows})` : ''}
              {v.id === 'warnings' && validation.warningRows ? ` (${validation.warningRows})` : ''}
            </option>
          ))}
        </select>
        <button type="button" className="admin-btn" onClick={handleAdd}>
          Add row
        </button>
        <button
          type="button"
          className="admin-btn admin-btn--danger"
          onClick={handleDeleteSelected}
          disabled={!selectedDeletable.length}
        >
          Delete selected{selectedDeletable.length ? ` (${selectedDeletable.length})` : ''}
        </button>
        {selectedDeleted.length > 0 && (
          <button
            type="button"
            className="admin-btn"
            onClick={() => {
              restoreRows(selectedDeleted);
              setSelectedIds(new Set());
            }}
          >
            Keep selected ({selectedDeleted.length})
          </button>
        )}
        <button
          type="button"
          className="admin-btn"
          onClick={() => downloadCsv('scale-r-draft.csv', rows.filter((r) => rowState(r.id) !== 'deleted'))}
        >
          Export CSV
        </button>

        <span className="admin-toolbar__spacer" />

        <button type="button" className="admin-btn" onClick={handleDiscard} disabled={!unsavedCount || Boolean(busy)}>
          Discard changes
        </button>
        <button
          type="button"
          className="admin-btn admin-btn--primary"
          onClick={handleSave}
          disabled={!unsavedCount || Boolean(busy)}
        >
          {busy === 'saving' ? 'Saving…' : 'Save draft'}
        </button>
        <button
          type="button"
          className="admin-btn admin-btn--publish"
          onClick={() => setPublishOpen(true)}
          disabled={Boolean(unsavedCount) || Boolean(busy)}
          title={unsavedCount ? 'Save or discard your changes before publishing' : undefined}
        >
          Publish{unpublishedCount ? ` (${unpublishedCount})` : ''}…
        </button>
      </div>

      {notice && (
        <p className={`admin-notice admin-notice--${notice.kind}`} role={notice.kind === 'error' ? 'alert' : 'status'}>
          {notice.text}
          <button type="button" className="admin-btn admin-btn--tiny" onClick={() => setNotice(null)}>
            Dismiss
          </button>
        </p>
      )}

      <div className="admin-page__body">
        <DataTable
          rows={viewRows}
          rowState={rowState}
          editedFields={editedFields}
          validation={validation}
          selectedIds={selectedIds}
          onToggleSelect={toggleSelect}
          onToggleSelectAll={toggleSelectAll}
          onUpdate={updateCell}
          onOpenRow={setOpenRowId}
          globalFilter={globalFilter}
          onGlobalFilterChange={setGlobalFilter}
          columnFilters={columnFilters}
          onColumnFiltersChange={setColumnFilters}
          sorting={sorting}
          onSortingChange={setSorting}
        />
        {openRow && (
          <RowEditor
            key={openRow.id}
            row={openRow}
            state={rowState(openRow.id)}
            issues={validation.byId.get(openRow.id)}
            onUpdate={updateCell}
            onToggleAutoId={setAutoProjectId}
            onClose={() => setOpenRowId(null)}
            onDelete={(id) => {
              deleteRows([id]);
              if (isNewRowId(id)) setOpenRowId(null);
            }}
            onRestore={(id) => restoreRows([id])}
            onRevert={revertRow}
          />
        )}
      </div>

      {publishOpen && (
        <PublishDialog
          onClose={() => setPublishOpen(false)}
          onPublished={(text) => setNotice({ kind: 'info', text })}
        />
      )}
    </div>
  );
}
