import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import Modal from './Modal.jsx';
import { VersionName } from './VersionsPage.jsx';
import { useDraft, useFilters } from './contexts.js';
import {
  CUSTOM_FILTER_COLUMNS,
  compactOptions,
  countFilterValues,
  defaultOptionLabel,
  describeFilterChanges,
  filterSpec,
  isBuiltInFilter,
  isPlainOption,
  isShownOnMap,
  mapOptions,
  optionKey,
  resolveOptions,
  sameSettings,
} from '../filters/filterConfig.js';
import { LOCAL_FILTERS, clearLocalFilterState } from '../filters/localFilters.js';

const formatDate = (iso) =>
  new Date(iso).toLocaleString('en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });

const plural = (n, word) => `${n.toLocaleString()} ${word}${n === 1 ? '' : 's'}`;

const filterVersionLabel = (v) => (v.name ? `"${v.name}" (filter v${v.version_no})` : `filter version ${v.version_no}`);

const columnLabel = (filter) =>
  CUSTOM_FILTER_COLUMNS.find((c) => c.column === filterSpec(filter).column)?.label ?? filterSpec(filter).column;

/** Writes the full on-screen order into the settings so it can be rearranged. */
function materialize(filter, resolved) {
  const byKey = new Map(filter.options.map((o) => [optionKey(filter.id, o.value), o]));
  return resolved.map((o) => byKey.get(o.key) ?? { value: o.value, visible: true });
}

function Switch({ checked, onChange, label, disabled }) {
  return (
    <label className="admin-switch" title={label}>
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} disabled={disabled} />
      <span aria-hidden="true" />
      <span className="sr-only">{label}</span>
    </label>
  );
}

function OptionRow({ filter, option, isNew, index, total, onPatch, onMove, onForget }) {
  const spec = filterSpec(filter);
  const missing = !option.inData;
  const placeholder = defaultOptionLabel(filter.id, option.value);
  return (
    <tr className={`${option.visible ? '' : 'is-hidden'} ${missing ? 'is-missing' : ''}`}>
      <td className="admin-fc__order">
        <button
          type="button"
          className="admin-btn admin-btn--tiny"
          onClick={() => onMove(index, -1)}
          disabled={index === 0}
          aria-label={`Move ${option.label} up`}
        >
          ▲
        </button>
        <button
          type="button"
          className="admin-btn admin-btn--tiny"
          onClick={() => onMove(index, 1)}
          disabled={index === total - 1}
          aria-label={`Move ${option.label} down`}
        >
          ▼
        </button>
      </td>
      <td>
        <div>{option.value}</div>
        <div className="admin-muted admin-fc__count">
          {missing ? 'No projects in the live data' : plural(option.count, 'project')}
          {isNew && <span className="admin-pill admin-pill--info">New in data</span>}
        </div>
      </td>
      <td>
        <input
          type="text"
          aria-label={`Label for ${option.value}`}
          value={
            option.configured
              ? (filter.options.find((o) => optionKey(filter.id, o.value) === option.key)?.label ?? '')
              : ''
          }
          placeholder={placeholder}
          maxLength={80}
          onChange={(e) => onPatch(option, { label: e.target.value })}
        />
      </td>
      {spec.colors && (
        <td>
          <input
            type="color"
            aria-label={`Color for ${option.value}`}
            value={option.color ?? '#95a5a6'}
            onChange={(e) => onPatch(option, { color: e.target.value })}
          />
        </td>
      )}
      {spec.definitions && (
        <td>
          <textarea
            rows={3}
            aria-label={`Definition for ${option.value}`}
            value={option.definition}
            placeholder="Shown in the info icon (leave empty for none)"
            onChange={(e) => onPatch(option, { definition: e.target.value })}
          />
        </td>
      )}
      <td>
        <Switch
          checked={option.visible}
          onChange={(on) => onPatch(option, { visible: on })}
          label={`Show ${option.value} on the map`}
        />
      </td>
      <td>
        {missing && (
          <button type="button" className="admin-btn admin-btn--link" onClick={() => onForget(option)}>
            Remove setting
          </button>
        )}
      </td>
    </tr>
  );
}

function FilterCard({ filter, index, total, dataValues, liveFilter, expanded, onToggle, onChange, onMove, onDelete }) {
  const spec = filterSpec(filter);
  const resolved = resolveOptions(filter, dataValues);
  const shown = resolved.filter((o) => o.visible && o.inData).length;
  const inData = resolved.filter((o) => o.inData).length;
  // "New" means neither the live map nor a real setting in the draft covers the
  // value. Settings that only hold a value's place (written when a value below
  // it is edited) do not count, so hiding one city takes exactly one off.
  const liveKeys = useMemo(
    () => new Set((liveFilter?.options ?? []).map((o) => optionKey(filter.id, o.value))),
    [liveFilter, filter.id],
  );
  const setKeys = new Set(filter.options.filter((o) => !isPlainOption(o)).map((o) => optionKey(filter.id, o.value)));
  const isNew = (o) => o.inData && !liveKeys.has(o.key) && !setKeys.has(o.key);
  const newValues = resolved.filter(isNew).length;
  const commit = (next) => onChange(compactOptions(next, dataValues, liveKeys));
  const edited = !liveFilter ? 'Added' : sameSettings(liveFilter, filter) ? null : 'Edited';

  const patchOption = (option, patch) => {
    // A value with no settings yet sits after the configured ones; writing the
    // values above it too keeps it in the same place on screen.
    const options = option.configured
      ? [...filter.options]
      : materialize(filter, resolved.slice(0, resolved.findIndex((o) => o.key === option.key) + 1));
    const i = options.findIndex((o) => optionKey(filter.id, o.value) === option.key);
    const next = { ...options[i], ...patch };
    if (next.label === '') delete next.label;
    options[i] = next;
    commit({ ...filter, options });
  };

  const moveOption = (i, delta) => {
    const options = materialize(filter, resolved);
    const [item] = options.splice(i, 1);
    options.splice(i + delta, 0, item);
    commit({ ...filter, options });
  };

  const forgetOption = (option) =>
    onChange({
      ...filter,
      options: filter.options.filter((o) => optionKey(filter.id, o.value) !== option.key),
    });

  return (
    <section className={`admin-fc ${filter.visible ? '' : 'is-hidden'}`} aria-label={`${filter.label} filter`}>
      <div className="admin-fc__head">
        <button
          type="button"
          className="admin-btn admin-btn--tiny"
          onClick={() => onMove(index, -1)}
          disabled={index === 0}
          aria-label={`Move ${filter.label} filter up`}
        >
          ▲
        </button>
        <button
          type="button"
          className="admin-btn admin-btn--tiny"
          onClick={() => onMove(index, 1)}
          disabled={index === total - 1}
          aria-label={`Move ${filter.label} filter down`}
        >
          ▼
        </button>
        <button type="button" className="admin-fc__title" onClick={onToggle} aria-expanded={expanded}>
          <span aria-hidden="true">{expanded ? '▾' : '▸'}</span> {filter.label}
        </button>
        <span className="admin-pill">
          {spec.kind === 'dropdown' ? 'Dropdown' : 'Checkboxes'} ·{' '}
          {isBuiltInFilter(filter.id) ? 'built in' : columnLabel(filter)}
        </span>
        <span className="admin-muted">
          {shown} of {inData} values shown
        </span>
        {newValues > 0 && <span className="admin-pill admin-pill--info">{plural(newValues, 'new value')} in data</span>}
        {edited && <span className="admin-pill admin-pill--warn">{edited}</span>}
        <span className="admin-toolbar__spacer" />
        {!isBuiltInFilter(filter.id) && (
          <button type="button" className="admin-btn admin-btn--small admin-btn--danger" onClick={onDelete}>
            Delete
          </button>
        )}
        <Switch
          checked={filter.visible}
          onChange={(on) => onChange({ ...filter, visible: on })}
          label={`Show the ${filter.label} filter on the map`}
        />
      </div>

      {expanded && (
        <div className="admin-fc__body">
          <label className="admin-field admin-fc__name">
            <span>Name shown on the map</span>
            <input
              type="text"
              value={filter.label}
              maxLength={60}
              onChange={(e) => onChange({ ...filter, label: e.target.value })}
            />
          </label>
          <p className="admin-muted">
            Values come from the live data; change them on the Project data page. Hiding a value removes it from this
            filter only. Its projects stay on the map.
          </p>
          {resolved.length === 0 ? (
            <p className="admin-muted">No project in the live data has a value in this column yet.</p>
          ) : (
            <table className="admin-table admin-fc__options">
              <thead>
                <tr>
                  <th scope="col">Order</th>
                  <th scope="col">Value in data</th>
                  <th scope="col">Label on the map</th>
                  {spec.colors && <th scope="col">Color</th>}
                  {spec.definitions && <th scope="col">Definition</th>}
                  <th scope="col">Shown</th>
                  <th scope="col">
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {resolved.map((option, i) => (
                  <OptionRow
                    key={option.key}
                    filter={filter}
                    option={option}
                    isNew={isNew(option)}
                    index={i}
                    total={resolved.length}
                    onPatch={patchOption}
                    onMove={moveOption}
                    onForget={forgetOption}
                  />
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </section>
  );
}

function AddFilterDialog({ usedColumns, onAdd, onClose }) {
  const available = CUSTOM_FILTER_COLUMNS.filter((c) => !usedColumns.has(c.column));
  const [column, setColumn] = useState(available[0]?.column ?? '');
  const [label, setLabel] = useState('');
  const chosen = available.find((c) => c.column === column);

  return (
    <Modal
      title="Add a filter"
      onClose={onClose}
      footer={
        <>
          <button type="button" className="admin-btn" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="admin-btn admin-btn--primary"
            disabled={!chosen}
            onClick={() => onAdd({ column, label: label.trim() || chosen.label })}
          >
            Add filter
          </button>
        </>
      }
    >
      {available.length === 0 ? (
        <p className="admin-muted">Every column that can be filtered already has a filter.</p>
      ) : (
        <>
          <label className="admin-field">
            <span>Project column it filters on</span>
            <select value={column} onChange={(e) => setColumn(e.target.value)}>
              {available.map((c) => (
                <option key={c.column} value={c.column}>
                  {c.label}
                </option>
              ))}
            </select>
          </label>
          <label className="admin-field">
            <span>Name shown on the map</span>
            <input
              type="text"
              value={label}
              maxLength={60}
              placeholder={chosen?.label}
              onChange={(e) => setLabel(e.target.value)}
            />
          </label>
          <p className="admin-muted">
            Its options are the values in that column of the live data. The filter is added to the draft; it appears on
            the map after you publish.
          </p>
        </>
      )}
    </Modal>
  );
}

function PublishFiltersDialog({ changes, firstPublish, onClose, onPublished }) {
  const { publish, busy } = useFilters();
  const [note, setNote] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState(null);
  const publishing = busy === 'publishing';

  const handlePublish = async () => {
    setError(null);
    const result = await publish(note.trim(), name.trim() || null);
    if (result.ok) {
      onPublished(
        LOCAL_FILTERS
          ? `Filter version ${result.result.version_no} is live on your local map (this browser only).`
          : `Filter version ${result.result.version_no} is live. Reload the public map to see it.`,
      );
      onClose();
    } else {
      setError(result.error);
    }
  };

  return (
    <Modal
      title="Publish filters to the public map"
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
            disabled={publishing || !note.trim()}
          >
            {publishing ? 'Publishing…' : 'Publish filters'}
          </button>
        </>
      }
    >
      {changes.length > 0 ? (
        <>
          <p>This changes the public map:</p>
          <ul>
            {changes.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        </>
      ) : (
        <p className="admin-muted">
          {firstPublish
            ? 'Nothing differs from the built-in filters. Publishing records them as the first filter version.'
            : 'Nothing differs from the live filters. Publishing still records a new filter version.'}
        </p>
      )}
      <p className="admin-muted">The current filters stay in the history, so you can switch back at any time.</p>
      <label className="admin-field">
        <span>Version name (optional)</span>
        <input
          type="text"
          value={name}
          maxLength={120}
          onChange={(e) => setName(e.target.value)}
          disabled={publishing}
        />
      </label>
      <label className="admin-field">
        <span>What changed? (required, shown in the filter history)</span>
        <textarea
          rows={3}
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="e.g. Added a Reported year filter; hid Infrastructure Failure"
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

function Preview({ config, dataByFilter }) {
  const shown = config.filters.filter((f) => f.visible);
  return (
    <aside className="admin-preview" aria-label="Preview of the map filters">
      <p className="admin-preview__caption">Preview: the map's filter panel with your draft</p>
      <div className="admin-preview__panel">
        {shown.length === 0 && <p className="admin-muted">No filters shown.</p>}
        {shown.map((filter) => {
          const options = mapOptions(filter, dataByFilter.get(filter.id) ?? []);
          return (
            <div key={filter.id} className="admin-preview__section">
              <div className="admin-preview__title">{filter.label || '(no name)'}</div>
              {filterSpec(filter).kind === 'dropdown' ? (
                <select aria-label={`${filter.label} preview`} className="admin-preview__select">
                  <option>All</option>
                  {options.map((o) => (
                    <option key={o.key}>{o.label}</option>
                  ))}
                </select>
              ) : (
                <div className="admin-preview__grid">
                  {options.map((o) => (
                    <span key={o.key} className="admin-preview__chip">
                      {o.color && filterSpec(filter).colors ? (
                        <i style={{ background: o.color }} aria-hidden="true" />
                      ) : (
                        <input type="checkbox" tabIndex={-1} readOnly aria-hidden="true" />
                      )}
                      {o.label}
                    </span>
                  ))}
                  {options.length === 0 && <span className="admin-muted">No values to show</span>}
                </div>
              )}
            </div>
          );
        })}
      </div>
      <p className="admin-muted">The public map only changes after you publish.</p>
    </aside>
  );
}

export default function LiveToolPage() {
  const { publishedRows, currentVersion, load: dataLoad } = useDraft();
  const {
    load,
    busy,
    versions,
    liveVersion,
    liveConfig,
    draft,
    setDraft,
    errors,
    hasUnsaved,
    hasUnpublished,
    differsFromLive,
    save,
    discard,
    makeLive,
    restore,
    resetToLive,
    rename,
    remove,
    reload,
  } = useFilters();
  const [expanded, setExpanded] = useState(() => new Set());
  const [adding, setAdding] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [notice, setNotice] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!hasUnsaved) return undefined;
    const warn = (event) => {
      event.preventDefault();
      event.returnValue = '';
    };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [hasUnsaved]);

  const projectsOnMap = useMemo(() => publishedRows.filter(isShownOnMap).length, [publishedRows]);

  const dataByFilter = useMemo(() => {
    const map = new Map();
    for (const filter of draft.filters) map.set(filter.id, countFilterValues(filter, publishedRows));
    return map;
  }, [draft.filters, publishedRows]);

  const changes = useMemo(() => describeFilterChanges(liveConfig, draft), [liveConfig, draft]);
  const liveById = useMemo(() => new Map(liveConfig.filters.map((f) => [f.id, f])), [liveConfig]);

  if (load.status === 'loading') return <p className="admin-page admin-muted">Loading the map filters…</p>;
  if (load.status === 'error') {
    return (
      <div className="admin-page">
        <p className="admin-error" role="alert">
          Could not load the map filters: {load.error}
        </p>
        <p className="admin-muted">
          If this mentions filters_draft or filters_versions, re-run supabase/sql/admin_dashboard.sql.
        </p>
      </div>
    );
  }

  const updateFilter = (index, next) =>
    setDraft((prev) => ({
      ...prev,
      filters: prev.filters.map((f, i) => (i === index ? next : f)),
    }));

  const moveFilter = (index, delta) =>
    setDraft((prev) => {
      const filters = [...prev.filters];
      const [item] = filters.splice(index, 1);
      filters.splice(index + delta, 0, item);
      return { ...prev, filters };
    });

  const deleteFilter = (filter) => {
    if (!window.confirm(`Delete the "${filter.label}" filter from the draft? The map keeps it until you publish.`))
      return;
    setDraft((prev) => ({
      ...prev,
      filters: prev.filters.filter((f) => f.id !== filter.id),
    }));
  };

  const addFilter = ({ column, label }) => {
    const id = `custom-${column}`;
    setDraft((prev) => ({
      ...prev,
      filters: [...prev.filters, { id, label, visible: true, options: [], column }],
    }));
    setExpanded((prev) => new Set(prev).add(id));
    setAdding(false);
  };

  const toggle = (id) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const act = async (fn, success) => {
    setError(null);
    setNotice(null);
    const result = await fn();
    if (!result) return;
    if (result.ok) {
      if (success) setNotice(typeof success === 'function' ? success(result.result) : success);
    } else {
      setError(result.error);
    }
  };

  const confirmLosingEdits = (action) =>
    window.confirm(
      `${action}${hasUnsaved || hasUnpublished ? '\n\nThis replaces the filter draft and discards its unpublished changes.' : ''}`,
    );

  const handleMakeLive = (v) =>
    act(
      async () => {
        if (!confirmLosingEdits(`Make ${filterVersionLabel(v)} live on the public map now?`)) return null;
        return makeLive(v.id);
      },
      `${filterVersionLabel(v).replace(/^f/, 'F')} is now live on the public map.`,
    );

  const handleRestore = (v) =>
    act(
      async () => {
        if (
          !confirmLosingEdits(
            `Load ${filterVersionLabel(v)} into the draft? The map does not change until you publish.`,
          )
        ) {
          return null;
        }
        return restore(v.id);
      },
      `Loaded ${filterVersionLabel(v)} into the draft.`,
    );

  const handleDelete = (v) =>
    act(async () => {
      if (!window.confirm(`Permanently delete ${filterVersionLabel(v)}? The map does not change.`)) return null;
      return remove(v.id);
    });

  const handleReset = () =>
    act(async () => {
      if (!confirmLosingEdits('Reset the filter draft to match the live map?')) return null;
      return resetToLive();
    }, 'The filter draft now matches the live map.');

  const usedColumns = new Set(draft.filters.map((f) => filterSpec(f).column));
  const shownLive = liveConfig.filters.filter((f) => f.visible).map((f) => f.label);

  return (
    <div className="admin-page admin-page--scroll">
      <div className="admin-page__intro">
        <h1 className="admin-title">Live tool</h1>
        <p className="admin-muted">
          What the public map shows right now, and the place to change which filters appear on it.
        </p>
      </div>

      {LOCAL_FILTERS && (
        <div className="admin-notice admin-notice--warning" role="note">
          <span>
            <strong>Local test mode.</strong> Saving and publishing filters only changes this browser; nothing is sent
            to Supabase. Open the local map at{' '}
            <a href="/dashboard" target="_blank" rel="noreferrer">
              /dashboard
            </a>{' '}
            to see it update as you publish.
          </span>
          <button
            type="button"
            className="admin-btn admin-btn--small"
            disabled={Boolean(busy)}
            onClick={() => {
              if (!window.confirm('Throw away the local test filters and start again from the real live filters?'))
                return;
              clearLocalFilterState();
              setNotice(null);
              setError(null);
              reload();
            }}
          >
            Start over
          </button>
        </div>
      )}

      {error && (
        <p className="admin-error" role="alert">
          {error}
        </p>
      )}
      {notice && (
        <p className="admin-notice admin-notice--info" role="status">
          {notice}
        </p>
      )}

      <div className="admin-live">
        <div className="admin-live__main">
          <section className="admin-card" aria-labelledby="live-now-title">
            <h2 id="live-now-title" className="admin-card__title">
              Live now
            </h2>
            <div className="admin-live__boxes">
              <div className="admin-live__box">
                <div className="admin-live__label">Dataset</div>
                <div className="admin-live__value">
                  {dataLoad.status === 'loading'
                    ? 'Loading…'
                    : currentVersion
                      ? currentVersion.name
                        ? `"${currentVersion.name}" (version ${currentVersion.version_no})`
                        : `Version ${currentVersion.version_no}`
                      : 'Not yet published'}
                </div>
                {currentVersion && (
                  <div className="admin-muted">
                    {plural(projectsOnMap, 'project')} on the map · published {formatDate(currentVersion.created_at)}
                    {currentVersion.created_by ? ` by ${currentVersion.created_by}` : ''}
                  </div>
                )}
                <Link to="/admin/versions" className="admin-btn admin-btn--small">
                  Change on the Versions page
                </Link>
              </div>
              <div className="admin-live__box">
                <div className="admin-live__label">Filters</div>
                <div className="admin-live__value">
                  {liveVersion
                    ? liveVersion.name
                      ? `"${liveVersion.name}" (filter version ${liveVersion.version_no})`
                      : `Filter version ${liveVersion.version_no}`
                    : 'Built-in filters (never published)'}
                </div>
                <div className="admin-muted">
                  {plural(shownLive.length, 'filter')} shown: {shownLive.join(', ') || 'none'}
                </div>
                {liveVersion && (
                  <div className="admin-muted">
                    Published {formatDate(liveVersion.created_at)}
                    {liveVersion.created_by ? ` by ${liveVersion.created_by}` : ''}
                  </div>
                )}
              </div>
            </div>
          </section>

          <section className="admin-card" aria-labelledby="filters-title">
            <div className="admin-card__head">
              <h2 id="filters-title" className="admin-card__title">
                Filters on the map
              </h2>
              <span className="admin-toolbar__spacer" />
              <button type="button" className="admin-btn" onClick={() => setAdding(true)}>
                + Add filter
              </button>
            </div>
            <p className="admin-muted">
              Top to bottom is the order on the map. Switch a filter off to hide it without deleting it. Open a filter
              to label, color, reorder or hide its values.
            </p>
            {draft.filters.map((filter, i) => (
              <FilterCard
                key={filter.id}
                filter={filter}
                index={i}
                total={draft.filters.length}
                dataValues={dataByFilter.get(filter.id) ?? []}
                liveFilter={liveById.get(filter.id)}
                expanded={expanded.has(filter.id)}
                onToggle={() => toggle(filter.id)}
                onChange={(next) => updateFilter(i, next)}
                onMove={moveFilter}
                onDelete={() => deleteFilter(filter)}
              />
            ))}
          </section>

          <div className="admin-savebar" role="region" aria-label="Filter changes">
            <span className={errors.length ? 'admin-error' : 'admin-muted'}>
              {errors.length
                ? errors[0]
                : hasUnsaved
                  ? 'Unsaved changes'
                  : hasUnpublished
                    ? 'Saved draft, not published yet'
                    : 'The draft matches the live map'}
            </span>
            <span className="admin-toolbar__spacer" />
            <button type="button" className="admin-btn" onClick={discard} disabled={!hasUnsaved || Boolean(busy)}>
              Discard
            </button>
            <button
              type="button"
              className="admin-btn"
              onClick={() => act(save, 'Filter draft saved.')}
              disabled={!hasUnsaved || errors.length > 0 || Boolean(busy)}
            >
              {busy === 'saving' ? 'Saving…' : 'Save draft'}
            </button>
            <button
              type="button"
              className="admin-btn admin-btn--publish"
              onClick={() => setPublishing(true)}
              disabled={(liveVersion && !differsFromLive) || errors.length > 0 || Boolean(busy)}
            >
              Publish filters…
            </button>
          </div>

          <section className="admin-card" aria-labelledby="filter-history-title">
            <div className="admin-card__head">
              <h2 id="filter-history-title" className="admin-card__title">
                Filter history
              </h2>
              <span className="admin-toolbar__spacer" />
              <button
                type="button"
                className="admin-btn admin-btn--small"
                onClick={handleReset}
                disabled={Boolean(busy)}
              >
                Reset draft to the live filters
              </button>
            </div>
            <p className="admin-muted">
              Every published set of filters is kept. <strong>Make live</strong> puts one straight back on the map;{' '}
              <strong>Restore to draft</strong> loads it here to edit first. Project data versions are separate and
              unaffected.
            </p>
            <table className="admin-table">
              <thead>
                <tr>
                  <th scope="col">Version</th>
                  <th scope="col">Published</th>
                  <th scope="col">By</th>
                  <th scope="col">Note</th>
                  <th scope="col">
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {versions.map((v) => (
                  <tr key={v.id} className={v.is_current ? 'is-current' : undefined}>
                    <td className="admin-table__version">
                      <VersionName version={v} onRename={rename} />
                    </td>
                    <td className="admin-table__date">{formatDate(v.created_at)}</td>
                    <td>{v.created_by}</td>
                    <td className="admin-table__note">{v.note}</td>
                    <td>
                      <div className="admin-table__actions">
                        {!v.is_current && (
                          <button
                            type="button"
                            className="admin-btn admin-btn--small admin-btn--primary"
                            onClick={() => handleMakeLive(v)}
                            disabled={Boolean(busy)}
                            aria-label={`Make filter version ${v.version_no} live`}
                          >
                            Make live
                          </button>
                        )}
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
                          aria-label={`Delete filter version ${v.version_no}`}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {versions.length === 0 && (
                  <tr>
                    <td colSpan={5} className="admin-muted">
                      Nothing published yet. The map uses its built-in filters until the first publish.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </section>
        </div>

        <Preview config={draft} dataByFilter={dataByFilter} />
      </div>

      {adding && <AddFilterDialog usedColumns={usedColumns} onAdd={addFilter} onClose={() => setAdding(false)} />}
      {publishing && (
        <PublishFiltersDialog
          changes={changes}
          firstPublish={!liveVersion}
          onClose={() => setPublishing(false)}
          onPublished={setNotice}
        />
      )}
    </div>
  );
}
