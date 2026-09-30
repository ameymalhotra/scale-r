import React, { useEffect, useRef, useState } from 'react';
import { FIELDS, isNewOption, parseFieldInput } from './fieldSchema.js';

const OTHER = '__other__';

/** Dropdown of a field's known options, with "Other…" for typing a new value. */
function ChoiceInput({ field, value, disabled, onCommit, describedBy }) {
  const [typing, setTyping] = useState(() => isNewOption(field, value));
  const [text, setText] = useState(value == null ? '' : String(value));
  useEffect(() => {
    setText(value == null ? '' : String(value));
    if (isNewOption(field, value)) setTyping(true);
  }, [field, value]);

  const known = field.options.find((o) => o.toLowerCase() === String(value ?? '').trim().toLowerCase());
  const commitText = () => {
    const next = parseFieldInput(field, text);
    if (next !== value) onCommit(next);
  };

  return (
    <div className="admin-choice">
      <select
        id={`row-editor-${field.key}`}
        value={typing ? OTHER : (known ?? '')}
        disabled={disabled}
        aria-describedby={describedBy}
        onChange={(e) => {
          if (e.target.value === OTHER) {
            setTyping(true);
            setText('');
            return;
          }
          setTyping(false);
          onCommit(e.target.value === '' ? null : e.target.value);
        }}
      >
        <option value="">(none)</option>
        {field.options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
        <option value={OTHER}>Other (type a new value)…</option>
      </select>
      {typing && (
        <input
          aria-label={`New ${field.label.toLowerCase()} value`}
          value={text}
          disabled={disabled}
          placeholder="Type the new value"
          onChange={(e) => setText(e.target.value)}
          onBlur={commitText}
          onKeyDown={(e) => {
            if (e.key === 'Enter') commitText();
          }}
        />
      )}
    </div>
  );
}

function FieldInput({ field, value, disabled, readOnly, onCommit, describedBy }) {
  const [text, setText] = useState(value == null ? '' : String(value));
  useEffect(() => {
    setText(value == null ? '' : String(value));
  }, [value]);

  const commit = () => {
    if (readOnly) return;
    const next = parseFieldInput(field, text);
    if (next !== value) onCommit(next);
  };
  const common = {
    id: `row-editor-${field.key}`,
    value: text,
    disabled,
    readOnly,
    'aria-describedby': describedBy,
    onChange: (e) => setText(e.target.value),
    onBlur: commit,
  };

  if (field.type === 'longtext') return <textarea rows={4} {...common} />;
  if (field.options && !readOnly) {
    return (
      <ChoiceInput field={field} value={value} disabled={disabled} onCommit={onCommit} describedBy={describedBy} />
    );
  }
  return (
    <input
      {...common}
      inputMode={field.type === 'number' ? 'decimal' : undefined}
      onKeyDown={(e) => {
        if (e.key === 'Enter') commit();
      }}
    />
  );
}

export default function RowEditor({
  row,
  state,
  issues,
  onUpdate,
  onToggleAutoId,
  onClose,
  onDelete,
  onRestore,
  onRevert,
}) {
  const closeRef = useRef(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;
  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (e) => {
      if (e.key === 'Escape' && !e.target.closest?.('.admin-cell__input')) onCloseRef.current();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  if (!row) return null;
  const deleted = state === 'deleted';
  const title = row.project_na || row.implementa || 'New project';

  return (
    <aside className="admin-drawer" role="dialog" aria-modal="false" aria-labelledby="row-editor-title">
      <header className="admin-drawer__head">
        <div>
          <h2 id="row-editor-title" className="admin-drawer__title">
            {title}
          </h2>
          <p className="admin-muted">
            {state === 'new' && 'New row (not saved yet)'}
            {state === 'edited' && 'Edited (not saved yet)'}
            {state === 'deleted' && 'Marked for deletion (not saved yet)'}
            {!state && 'Saved in the draft'}
          </p>
        </div>
        <button ref={closeRef} type="button" className="admin-btn admin-btn--small" onClick={onClose}>
          Close
        </button>
      </header>

      <div className="admin-drawer__body">
        {FIELDS.map((field) => {
          const error = issues?.errors?.[field.key];
          const warning = issues?.warnings?.[field.key];
          const messageId = error || warning ? `row-editor-${field.key}-msg` : undefined;
          const autoIdField = field.key === 'implementa' && state === 'new';
          const autoId = autoIdField && row._autoId;
          return (
            <div key={field.key} className="admin-field">
              <label htmlFor={`row-editor-${field.key}`}>
                {field.label}
                {field.required && <span aria-hidden="true"> *</span>}
                {field.readOnly && <span className="admin-muted"> (assigned automatically on save)</span>}
              </label>
              <FieldInput
                field={field}
                value={row[field.key]}
                disabled={deleted}
                readOnly={field.readOnly || autoId}
                describedBy={messageId}
                onCommit={(next) => onUpdate(row.id, field.key, next)}
              />
              {autoIdField && (
                <label className="admin-field__toggle">
                  <input
                    type="checkbox"
                    checked={Boolean(row._autoId)}
                    onChange={(e) => onToggleAutoId(row.id, e.target.checked)}
                  />
                  Generate the next Project ID automatically
                </label>
              )}
              {error && (
                <p id={messageId} className="admin-error">
                  {error}
                </p>
              )}
              {!error && warning && (
                <p id={messageId} className="admin-warning">
                  {warning}
                </p>
              )}
            </div>
          );
        })}
      </div>

      <footer className="admin-drawer__foot">
        {deleted ? (
          <button type="button" className="admin-btn" onClick={() => onRestore(row.id)}>
            Keep this row
          </button>
        ) : (
          <button type="button" className="admin-btn admin-btn--danger" onClick={() => onDelete(row.id)}>
            {state === 'new' ? 'Remove new row' : 'Delete row'}
          </button>
        )}
        {state === 'edited' && (
          <button type="button" className="admin-btn" onClick={() => onRevert(row.id)}>
            Undo edits to this row
          </button>
        )}
      </footer>
    </aside>
  );
}
