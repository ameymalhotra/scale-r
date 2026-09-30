import React from 'react';
import { FIELD_BY_KEY, formatFieldValue } from './fieldSchema.js';

const LIMIT = 150;

const rowTitle = (row) => row.project_na || row.implementa || `Row ${row.id}`;

function show(field, value) {
  const text = formatFieldValue(field, value);
  return text === '' ? <em className="admin-muted">blank</em> : text;
}

function Section({ title, items, render }) {
  if (!items.length) return null;
  return (
    <section className="admin-diff__section">
      <h3>
        {title} ({items.length})
      </h3>
      <ul>
        {items.slice(0, LIMIT).map(render)}
        {items.length > LIMIT && <li className="admin-muted">…and {items.length - LIMIT} more</li>}
      </ul>
    </section>
  );
}

/** Renders the output of diffRows(). `labels` lets callers phrase the direction. */
export default function DiffView({ diff, labels = {} }) {
  const { added, removed, modified } = diff;
  if (!added.length && !removed.length && !modified.length) {
    return <p className="admin-muted">No differences.</p>;
  }

  return (
    <div className="admin-diff">
      <p className="admin-diff__summary">
        <span className="admin-pill admin-pill--add">{added.length} added</span>
        <span className="admin-pill admin-pill--info">{modified.length} edited</span>
        <span className="admin-pill admin-pill--remove">{removed.length} removed</span>
      </p>
      <Section
        title={labels.modified ?? 'Edited'}
        items={modified}
        render={(m) => (
          <li key={m.id}>
            <strong>{rowTitle(m.after)}</strong>
            <ul className="admin-diff__fields">
              {m.fields.map((key) => {
                const field = FIELD_BY_KEY[key];
                return (
                  <li key={key}>
                    {field.label}: <del>{show(field, m.before[key])}</del> → <ins>{show(field, m.after[key])}</ins>
                  </li>
                );
              })}
            </ul>
          </li>
        )}
      />
      <Section
        title={labels.added ?? 'Added'}
        items={added}
        render={(row) => (
          <li key={row.id}>
            <strong>{rowTitle(row)}</strong>
            {row.city ? ` — ${row.city}` : ''}
          </li>
        )}
      />
      <Section
        title={labels.removed ?? 'Removed'}
        items={removed}
        render={(row) => (
          <li key={row.id}>
            <strong>{rowTitle(row)}</strong>
            {row.city ? ` — ${row.city}` : ''}
          </li>
        )}
      />
    </div>
  );
}
