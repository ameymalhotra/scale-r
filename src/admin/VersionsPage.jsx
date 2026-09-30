import React, { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import DiffView from './DiffView.jsx';
import Modal from './Modal.jsx';
import { fetchVersionSnapshot } from './api.js';
import { downloadCsv } from './csv.js';
import { diffRows } from './diff.js';
import { useDraft } from './contexts.js';

const formatDate = (iso) =>
  new Date(iso).toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' });

const versionLabel = (v) => (v.name ? `"${v.name}" (v${v.version_no})` : `version ${v.version_no}`);

function VersionName({ version, onRename }) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const start = () => {
    setText(version.name ?? '');
    setError(null);
    setEditing(true);
  };

  const save = async () => {
    if (text.trim() === (version.name ?? '')) {
      setEditing(false);
      return;
    }
    setSaving(true);
    const result = await onRename(version.id, text);
    setSaving(false);
    if (result.ok) setEditing(false);
    else setError(result.error);
  };

  if (editing) {
    return (
      <form
        className="admin-version-name__form"
        onSubmit={(e) => {
          e.preventDefault();
          save();
        }}
      >
        <input
          aria-label={`Name for version ${version.version_no}`}
          value={text}
          maxLength={120}
          placeholder={`Version ${version.version_no}`}
          disabled={saving}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Escape') setEditing(false);
          }}
          // eslint-disable-next-line jsx-a11y/no-autofocus
          autoFocus
        />
        <button type="submit" className="admin-btn admin-btn--small admin-btn--primary" disabled={saving}>
          Save
        </button>
        <button type="button" className="admin-btn admin-btn--small" onClick={() => setEditing(false)} disabled={saving}>
          Cancel
        </button>
        {error && (
          <p className="admin-error" role="alert">
            {error}
          </p>
        )}
      </form>
    );
  }

  return (
    <div className="admin-version-name">
      <span className="admin-version-name__label">{version.name || `Version ${version.version_no}`}</span>
      {version.name && <span className="admin-muted"> v{version.version_no}</span>}
      {version.is_current && <span className="admin-pill admin-pill--add">live</span>}
      <button
        type="button"
        className="admin-btn admin-btn--link"
        onClick={start}
        aria-label={`Rename version ${version.version_no}`}
      >
        Rename
      </button>
    </div>
  );
}

export default function VersionsPage({ loadSnapshot = fetchVersionSnapshot }) {
  const {
    client,
    versions,
    publishedRows,
    unsavedCount,
    unpublishedCount,
    restoreVersion,
    renameVersion,
    deleteVersion,
    makeVersionLive,
    rebuildMapFile,
    resetDraft,
    busy,
  } = useDraft();
  const [notice, setNotice] = useState(null);
  const navigate = useNavigate();
  const snapshots = useRef(new Map());
  const [loadingId, setLoadingId] = useState(null);
  const [compare, setCompare] = useState(null);
  const [error, setError] = useState(null);

  const getSnapshot = async (version) => {
    if (!snapshots.current.has(version.id)) {
      setLoadingId(version.id);
      try {
        snapshots.current.set(version.id, await loadSnapshot(client, version.id));
      } finally {
        setLoadingId(null);
      }
    }
    return snapshots.current.get(version.id);
  };

  const run = async (fn) => {
    setError(null);
    setNotice(null);
    try {
      await fn();
    } catch (e) {
      setError(e.message);
    }
  };

  const handleCompare = (version) =>
    run(async () => {
      const snapshot = await getSnapshot(version);
      setCompare({ version, diff: diffRows(publishedRows, snapshot) });
    });

  const handleDownload = (version) =>
    run(async () => {
      downloadCsv(`scale-r-version-${version.version_no}.csv`, await getSnapshot(version));
    });

  const confirmReplacingDraft = (action) => {
    const losses = draftLosses();
    const warning = losses.length ? `\n\nThis replaces the current draft and discards ${losses.join(' and ')}.` : '';
    return window.confirm(`${action}${warning}\n\nThe public map does not change until you publish.`);
  };

  const handleRestore = (version) =>
    run(async () => {
      if (!confirmReplacingDraft(`Load ${versionLabel(version)} into the draft?`)) return;
      const result = await restoreVersion(version.id);
      if (!result.ok) throw new Error(result.error);
      navigate('/admin');
    });

  const draftLosses = () => {
    const losses = [];
    if (unsavedCount) losses.push(`${unsavedCount} unsaved change${unsavedCount === 1 ? '' : 's'}`);
    if (unpublishedCount) {
      losses.push(`${unpublishedCount} saved but unpublished row change${unpublishedCount === 1 ? '' : 's'}`);
    }
    return losses;
  };

  const handleMakeLive = (version) =>
    run(async () => {
      const losses = draftLosses();
      const ok = window.confirm(
        `Make ${versionLabel(version)} live on the public map now?\n\n` +
          `The map will show its ${version.row_count.toLocaleString()} projects, and the draft is reset to match it.` +
          (losses.length ? ` This discards ${losses.join(' and ')}.` : '') +
          '\n\nNo new version is created; you can switch back to any other version the same way.',
      );
      if (!ok) return;
      const result = await makeVersionLive(version.id);
      if (!result.ok) throw new Error(result.error);
      setNotice(`${versionLabel(version).replace(/^v/, 'V')} is now live on the public map.`);
    });

  const handleRebuild = () =>
    run(async () => {
      const result = await rebuildMapFile();
      if (!result.ok) throw new Error(result.error);
      setNotice(`Map file rebuilt from the live data (${result.result.features.toLocaleString()} projects).`);
    });

  const handleDelete = (version) =>
    run(async () => {
      const ok = window.confirm(
        `Permanently delete ${versionLabel(version)}?\n\n` +
          'Its snapshot of the data is removed and cannot be restored afterwards. ' +
          'Download it as CSV first if you may need it. The public map does not change.',
      );
      if (!ok) return;
      snapshots.current.delete(version.id);
      const result = await deleteVersion(version.id);
      if (!result.ok) throw new Error(result.error);
    });

  const handleReset = () =>
    run(async () => {
      if (!confirmReplacingDraft('Reset the draft to match the live map?')) return;
      const result = await resetDraft();
      if (!result.ok) throw new Error(result.error);
    });

  return (
    <div className="admin-page admin-page--scroll">
      <div className="admin-page__intro">
        <h1 className="admin-title">Version history</h1>
        <p className="admin-muted">
          Every publish is saved here. <strong>Make live</strong> puts a version straight back on the public map.{' '}
          <strong>Restore to draft</strong> loads it into the draft instead, so you can edit it before publishing it as a
          new version.
        </p>
        <button type="button" className="admin-btn" onClick={handleReset} disabled={Boolean(busy)}>
          Reset draft to the live map
        </button>
      </div>

      {error && (
        <p className="admin-error" role="alert">
          {error}
        </p>
      )}
      {notice && (
        <p className="admin-notice" role="status">
          {notice}
        </p>
      )}

      <table className="admin-table">
        <thead>
          <tr>
            <th scope="col">Version</th>
            <th scope="col">Published</th>
            <th scope="col">By</th>
            <th scope="col">Note</th>
            <th scope="col" className="is-number">
              Projects
            </th>
            <th scope="col">
              <span className="sr-only">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {versions.map((v) => (
            <tr key={v.id} className={v.is_current ? 'is-current' : undefined}>
              <td>
                <VersionName version={v} onRename={renameVersion} />
              </td>
              <td>{formatDate(v.created_at)}</td>
              <td>{v.created_by}</td>
              <td className="admin-table__note">{v.note}</td>
              <td className="is-number">{v.row_count.toLocaleString()}</td>
              <td className="admin-table__actions">
                {v.is_current ? (
                  <button
                    type="button"
                    className="admin-btn admin-btn--small"
                    onClick={handleRebuild}
                    disabled={Boolean(busy)}
                    title="Rewrite the public map file from the live data. No data changes."
                  >
                    Rebuild map file
                  </button>
                ) : (
                  <button
                    type="button"
                    className="admin-btn admin-btn--small admin-btn--primary"
                    onClick={() => handleMakeLive(v)}
                    disabled={Boolean(busy)}
                    aria-label={`Make version ${v.version_no} live`}
                  >
                    Make live
                  </button>
                )}
                <button
                  type="button"
                  className="admin-btn admin-btn--small"
                  onClick={() => handleCompare(v)}
                  disabled={loadingId === v.id || v.is_current}
                >
                  Compare with live
                </button>
                <button
                  type="button"
                  className="admin-btn admin-btn--small"
                  onClick={() => handleDownload(v)}
                  disabled={loadingId === v.id}
                >
                  Download CSV
                </button>
                <button
                  type="button"
                  className="admin-btn admin-btn--small"
                  onClick={() => handleRestore(v)}
                  disabled={Boolean(busy)}
                >
                  Restore to draft
                </button>
                <button
                  type="button"
                  className="admin-btn admin-btn--small admin-btn--danger"
                  onClick={() => handleDelete(v)}
                  disabled={Boolean(busy) || v.is_current}
                  title={v.is_current ? 'The live version cannot be deleted' : undefined}
                  aria-label={`Delete version ${v.version_no}`}
                >
                  Delete
                </button>
              </td>
            </tr>
          ))}
          {versions.length === 0 && (
            <tr>
              <td colSpan={6} className="admin-muted">
                No versions yet. Run supabase/sql/admin_dashboard.sql to record version 1.
              </td>
            </tr>
          )}
        </tbody>
      </table>

      {compare && (
        <Modal
          title={`Restoring ${versionLabel(compare.version)} would change the live map like this`}
          onClose={() => setCompare(null)}
        >
          <DiffView
            diff={compare.diff}
            labels={{
              added: 'Would come back',
              removed: 'Would be removed',
              modified: 'Would change',
            }}
          />
        </Modal>
      )}
    </div>
  );
}
