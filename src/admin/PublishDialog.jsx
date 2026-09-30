import React, { useState } from 'react';
import DiffView from './DiffView.jsx';
import Modal from './Modal.jsx';
import { useDraft } from './contexts.js';

export default function PublishDialog({ onClose, onPublished }) {
  const { unpublishedDiff, unpublishedCount, validation, currentVersion, serverRows, publish, busy } = useDraft();
  const [note, setNote] = useState('');
  const [error, setError] = useState(null);

  const publishing = busy === 'publishing';
  const blocked = validation.errorRows > 0;
  const nextVersion = (currentVersion?.version_no ?? 0) + 1;

  const handlePublish = async () => {
    setError(null);
    const result = await publish(note.trim());
    if (result.ok) {
      onPublished(
        `Published version ${result.result.version_no} (${result.result.row_count.toLocaleString()} projects). ` +
          'The public map picks it up within about a minute.',
      );
      onClose();
    } else {
      setError(result.error);
    }
  };

  return (
    <Modal
      title={`Publish version ${nextVersion} to the public map`}
      onClose={onClose}
      busy={publishing}
      footer={
        <>
          <button type="button" className="admin-btn" onClick={onClose} disabled={publishing}>
            Cancel
          </button>
          <button
            type="button"
            className="admin-btn admin-btn--publish"
            onClick={handlePublish}
            disabled={publishing || blocked || !note.trim()}
          >
            {publishing ? 'Publishing…' : `Publish ${serverRows.length.toLocaleString()} projects`}
          </button>
        </>
      }
    >
      <p>
        {currentVersion
          ? `Changes compared with the live map (version ${currentVersion.version_no}):`
          : 'Changes compared with the live map:'}
      </p>
      {unpublishedCount === 0 && (
        <p className="admin-muted">
          The draft is identical to the live map. Publishing will still record a new version with your note.
        </p>
      )}
      <DiffView diff={unpublishedDiff} />

      {blocked && (
        <p className="admin-error" role="alert">
          {validation.errorRows} row{validation.errorRows === 1 ? ' has' : 's have'} errors. Close this dialog, choose
          “Rows with errors” in the table, and fix them before publishing.
        </p>
      )}

      <label className="admin-field">
        <span>What changed? (required, shown in the version history)</span>
        <textarea
          rows={3}
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="e.g. Added October LMS projects; corrected Coral Gables costs"
          disabled={publishing}
        />
      </label>

      {error && (
        <p className="admin-error" role="alert">
          {error}
        </p>
      )}
    </Modal>
  );
}
