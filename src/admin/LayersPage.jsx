import React, { useEffect, useMemo, useState } from 'react';
import Modal from './Modal.jsx';
import LayerEditor from './LayerEditor.jsx';
import LayerPreviewMap from './LayerPreviewMap.jsx';
import { VersionName } from './VersionsPage.jsx';
import { useLayers } from './contexts.js';
import {
  GEOMETRY_LABELS,
  MAX_LAYER_FILE_BYTES,
  MODE_LABELS,
  createLayer,
  describeLayerChanges,
  inspectGeojson,
  newLayerId,
  normalizeLayer,
  sameLayerSettings,
} from '../layers/layerConfig.js';
import LayerLegend from '../layers/LayerLegend.jsx';
import { builtinDefinition } from '../layers/builtinRegistry.js';
import BuiltinLayerEditor from './BuiltinLayerEditor.jsx';
import { LOCAL_FILTERS } from '../filters/localFilters.js';
import { LOCAL_LAYERS, clearLocalLayerState } from '../layers/localLayers.js';
import { reprojectFeatureCollectionIfNeeded } from '../utils/geoProcessing.js';

const formatDate = (iso) =>
  new Date(iso).toLocaleString('en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });

const plural = (n, word) => `${n.toLocaleString()} ${word}${n === 1 ? '' : 's'}`;

const layerVersionLabel = (v) => (v.name ? `"${v.name}" (layer v${v.version_no})` : `layer version ${v.version_no}`);

const formatBytes = (bytes) =>
  bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;

function readFileText(file) {
  if (typeof file.text === 'function') return file.text();
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(reader.error);
    reader.readAsText(file);
  });
}

/** Parses, checks and reprojects an uploaded file. Resolves to { geojson, info }. */
async function readLayerFile(file) {
  if (!/\.(geo)?json$/i.test(file.name)) throw new Error('Choose a .geojson or .json file.');
  if (file.size > MAX_LAYER_FILE_BYTES) {
    throw new Error(
      `The file is ${formatBytes(file.size)}; the limit is ${formatBytes(MAX_LAYER_FILE_BYTES)}. Simplify it or drop unused attributes first.`,
    );
  }
  let data;
  try {
    data = JSON.parse(await readFileText(file));
  } catch {
    throw new Error('The file is not valid JSON.');
  }
  const info = inspectGeojson(data);
  const geojson = reprojectFeatureCollectionIfNeeded(data);
  return { geojson, info };
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

/** Upload a new layer, or replace the data of `replacing`. */
function UploadDialog({ replacing, usedLabels, onUploaded, onClose }) {
  const { uploadFile, busy } = useLayers();
  const [file, setFile] = useState(null);
  const [parsed, setParsed] = useState(null);
  const [label, setLabel] = useState('');
  const [description, setDescription] = useState('');
  const [error, setError] = useState(null);
  const uploading = busy === 'uploading';

  const choose = async (chosen) => {
    setFile(chosen);
    setParsed(null);
    setError(null);
    if (!chosen) return;
    try {
      const result = await readLayerFile(chosen);
      if (replacing && result.info.geometry !== replacing.geometry) {
        throw new Error(
          `"${replacing.label}" is a ${GEOMETRY_LABELS[replacing.geometry].toLowerCase()} layer; this file has ${GEOMETRY_LABELS[result.info.geometry].toLowerCase()}. Upload it as a new layer instead.`,
        );
      }
      setParsed(result);
      if (!label) setLabel(chosen.name.replace(/\.(geo)?json$/i, '').replace(/[_-]+/g, ' ').trim().slice(0, 60));
    } catch (e) {
      setError(e.message);
    }
  };

  const name = label.trim();
  const duplicate = !replacing && usedLabels.has(name.toLowerCase());

  const upload = async () => {
    setError(null);
    try {
      const id = replacing?.id ?? newLayerId();
      const path = await uploadFile(id, parsed.geojson);
      onUploaded({ id, path, info: parsed.info, label: name, description: description.trim() });
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <Modal
      title={replacing ? `Replace the data of "${replacing.label}"` : 'Upload a map layer'}
      onClose={onClose}
      busy={uploading}
      footer={
        <>
          <button type="button" className="admin-btn" onClick={onClose} disabled={uploading}>
            Cancel
          </button>
          <button
            type="button"
            className="admin-btn admin-btn--primary"
            onClick={upload}
            disabled={!parsed || uploading || (!replacing && (!name || duplicate))}
          >
            {uploading ? 'Uploading…' : replacing ? 'Replace data' : 'Upload layer'}
          </button>
        </>
      }
    >
      <label className="admin-field">
        <span>GeoJSON file (.geojson or .json, up to {formatBytes(MAX_LAYER_FILE_BYTES)})</span>
        <input
          type="file"
          accept=".geojson,.json,application/geo+json,application/json"
          onChange={(e) => choose(e.target.files?.[0] ?? null)}
          disabled={uploading}
        />
      </label>
      {file && parsed && (
        <p className="admin-notice admin-notice--info" role="status">
          {GEOMETRY_LABELS[parsed.info.geometry]}: {plural(parsed.info.featureCount, 'feature')},{' '}
          {plural(parsed.info.fields.length, 'attribute')} ({formatBytes(file.size)}).
        </p>
      )}
      {!replacing && (
        <>
          <label className="admin-field">
            <span>Name shown on the map</span>
            <input type="text" value={label} maxLength={60} onChange={(e) => setLabel(e.target.value)} disabled={uploading} />
          </label>
          {duplicate && <p className="admin-error">Another layer already has this name.</p>}
          <label className="admin-field">
            <span>Description (optional, admin only)</span>
            <input
              type="text"
              value={description}
              maxLength={300}
              onChange={(e) => setDescription(e.target.value)}
              disabled={uploading}
            />
          </label>
        </>
      )}
      <p className="admin-muted">
        Coordinates in Web Mercator are converted to longitude and latitude. The file is stored right away; the layer
        appears on the map only after you publish.
      </p>
      {error && (
        <p className="admin-error" role="alert">
          {error}
        </p>
      )}
    </Modal>
  );
}

function PublishLayersDialog({ changes, firstPublish, onClose, onPublished }) {
  const { publish, busy } = useLayers();
  const [note, setNote] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState(null);
  const publishing = busy === 'publishing';

  const handlePublish = async () => {
    setError(null);
    const result = await publish(note.trim(), name.trim() || null);
    if (result.ok) {
      onPublished(
        LOCAL_LAYERS
          ? `Layer version ${result.result.version_no} is live on your local map (this browser only).`
          : `Layer version ${result.result.version_no} is live. Reload the public map to see it.`,
      );
      onClose();
    } else {
      setError(result.error);
    }
  };

  return (
    <Modal
      title="Publish layers to the public map"
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
            {publishing ? 'Publishing…' : 'Publish layers'}
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
            ? 'There are no uploaded layers. Publishing records an empty first layer version.'
            : 'Nothing differs from the live layers. Publishing still records a new layer version.'}
        </p>
      )}
      <p className="admin-muted">The current layers stay in the history, so you can switch back at any time.</p>
      <label className="admin-field">
        <span>Version name (optional)</span>
        <input type="text" value={name} maxLength={120} onChange={(e) => setName(e.target.value)} disabled={publishing} />
      </label>
      <label className="admin-field">
        <span>What changed? (required, shown in the layer history)</span>
        <textarea
          rows={3}
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="e.g. Added the 2040 sea level rise inundation layer"
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

function LayerCard({ layer, index, total, liveLayer, expanded, onToggle, onChange, onMove, onRemove, onReplace, loadGeojson }) {
  const builtin = builtinDefinition(layer.id);
  const edited = !liveLayer ? 'New' : sameLayerSettings(liveLayer, layer) ? null : 'Edited';
  return (
    <section className={`admin-fc ${layer.visible ? '' : 'is-hidden'}`} aria-label={`${layer.label || 'Unnamed'} layer`}>
      <div className="admin-fc__head">
        <button
          type="button"
          className="admin-btn admin-btn--tiny"
          onClick={() => onMove(index, -1)}
          disabled={index === 0}
          aria-label={`Move ${layer.label} layer up`}
        >
          ▲
        </button>
        <button
          type="button"
          className="admin-btn admin-btn--tiny"
          onClick={() => onMove(index, 1)}
          disabled={index === total - 1}
          aria-label={`Move ${layer.label} layer down`}
        >
          ▼
        </button>
        <button type="button" className="admin-fc__title" onClick={onToggle} aria-expanded={expanded}>
          <span aria-hidden="true">{expanded ? '▾' : '▸'}</span> {layer.label || '(no name)'}
        </button>
        <span className="admin-pill">
          {builtin?.group ? 'Layer group' : `${GEOMETRY_LABELS[layer.geometry]} · ${builtin ? 'Built-in' : plural(layer.featureCount, 'feature')}`}
        </span>
        <span className="admin-pill">{MODE_LABELS[layer.symbology.mode]}</span>
        {edited && <span className="admin-pill admin-pill--warn">{edited}</span>}
        <span className="admin-toolbar__spacer" />
        {!builtin && <button type="button" className="admin-btn admin-btn--small admin-btn--danger" onClick={onRemove}>
          Remove
        </button>}
        <Switch
          checked={layer.visible}
          onChange={(on) => onChange({ ...layer, visible: on })}
          label={`Show the ${layer.label} layer on the map`}
        />
      </div>
      {expanded && (builtin ? <BuiltinLayerEditor layer={layer} onChange={onChange} /> : <LayerEditor layer={layer} onChange={onChange} loadGeojson={loadGeojson} onReplace={onReplace} />)}
    </section>
  );
}

function Preview({ layer, loadGeojson, showMap }) {
  const [loaded, setLoaded] = useState({ file: null, data: null, error: null });

  useEffect(() => {
    if (!layer || !showMap) return undefined;
    let cancelled = false;
    loadGeojson(layer.file).then(
      (data) => !cancelled && setLoaded({ file: layer.file, data, error: null }),
      (e) => !cancelled && setLoaded({ file: layer.file, data: null, error: e.message }),
    );
    return () => {
      cancelled = true;
    };
  }, [layer, showMap, loadGeojson]);

  const geojson = layer && loaded.file === layer.file ? loaded.data : null;

  return (
    <aside className="admin-preview admin-preview--layers" aria-label="Preview of the selected layer">
      <p className="admin-preview__caption">
        Preview{layer ? `: ${layer.label || '(no name)'}` : ''} with your draft symbology
      </p>
      {layer ? (
        <>
          {showMap && <LayerPreviewMap layer={layer} geojson={geojson} />}
          {loaded.error && loaded.file === layer.file && <p className="admin-error">{loaded.error}</p>}
          <div className="admin-preview__panel">
            <div className="admin-preview__title">{layer.label || '(no name)'}</div>
            <LayerLegend layer={layer} />
          </div>
        </>
      ) : (
        <div className="admin-preview__panel">
          <p className="admin-muted">Open a layer to preview it.</p>
        </div>
      )}
      <p className="admin-muted">The public map only changes after you publish.</p>
    </aside>
  );
}

export default function LayersPage({ showPreviewMap = true }) {
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
    loadGeojson,
  } = useLayers();
  const [expandedId, setExpandedId] = useState(null);
  const [upload, setUpload] = useState(null);
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

  const changes = useMemo(() => describeLayerChanges(liveConfig, draft), [liveConfig, draft]);
  const liveById = useMemo(() => new Map([...liveConfig.builtins, ...liveConfig.layers].map((l) => [l.id, l])), [liveConfig]);

  if (load.status === 'loading') return <p className="admin-page admin-muted">Loading the map layers…</p>;
  if (load.status === 'error') {
    return (
      <div className="admin-page">
        <p className="admin-error" role="alert">
          Could not load the map layers: {load.error}
        </p>
        <p className="admin-muted">
          If this mentions layers_draft or layers_versions, re-run supabase/sql/admin_dashboard.sql.
        </p>
      </div>
    );
  }

  const updateLayer = (id, next) =>
    setDraft((prev) => ({ ...prev, [builtinDefinition(id) ? 'builtins' : 'layers']: prev[builtinDefinition(id) ? 'builtins' : 'layers'].map((l) => (l.id === id ? next : l)) }));

  const removeLayer = (layer) => {
    if (!window.confirm(`Remove the "${layer.label}" layer from the draft? The map keeps it until you publish.`)) return;
    setDraft((prev) => ({ ...prev, layers: prev.layers.filter((l) => l.id !== layer.id), order: prev.order.filter((id) => id !== layer.id) }));
  };

  const handleUploaded = ({ id, path, info, label, description }) => {
    const replacing = upload?.replacing;
    if (replacing) {
      const current = draft.layers.find((l) => l.id === replacing.id) ?? replacing;
      const next = normalizeLayer({ ...current, file: path, featureCount: info.featureCount, fields: info.fields });
      updateLayer(replacing.id, next);
      setNotice(`New data uploaded for "${current.label}". Check its symbology, then save or publish.`);
    } else {
      const layer = createLayer({ id, file: path, label, description, info });
      setDraft((prev) => ({ ...prev, layers: [...prev.layers, layer], order: [...prev.order, layer.id] }));
      setExpandedId(id);
      setNotice(`"${label}" uploaded. Set its symbology, then save or publish.`);
    }
    setUpload(null);
  };

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
      `${action}${hasUnsaved || hasUnpublished ? '\n\nThis replaces the layer draft and discards its unpublished changes.' : ''}`,
    );

  const handleMakeLive = (v) =>
    act(
      async () => {
        if (!confirmLosingEdits(`Make ${layerVersionLabel(v)} live on the public map now?`)) return null;
        return makeLive(v.id);
      },
      `${layerVersionLabel(v).replace(/^l/, 'L')} is now live on the public map.`,
    );

  const handleRestore = (v) =>
    act(
      async () => {
        if (!confirmLosingEdits(`Load ${layerVersionLabel(v)} into the draft? The map does not change until you publish.`)) {
          return null;
        }
        return restore(v.id);
      },
      `Loaded ${layerVersionLabel(v)} into the draft.`,
    );

  const handleDelete = (v) =>
    act(async () => {
      if (!window.confirm(`Permanently delete ${layerVersionLabel(v)}? The map does not change.`)) return null;
      return remove(v.id);
    });

  const handleReset = () =>
    act(async () => {
      if (!confirmLosingEdits('Reset the layer draft to match the live map?')) return null;
      return resetToLive();
    }, 'The layer draft now matches the live map.');

  const usedLabels = new Set([...draft.builtins, ...draft.layers].map((l) => l.label.trim().toLowerCase()));
  const shownLive = [...liveConfig.builtins, ...liveConfig.layers].filter((l) => l.visible && !builtinDefinition(l.id)?.parent).map((l) => l.label);
  const allLayers = [...draft.builtins, ...draft.layers];
  const selectedPreview = allLayers.find((l) => l.id === expandedId && !builtinDefinition(l.id)?.group) ?? null;
  const previewLayer = selectedPreview && builtinDefinition(selectedPreview.id)?.parent
    ? { ...selectedPreview, style: { ...selectedPreview.style, opacity: selectedPreview.style.opacity * draft.builtins.find((l) => l.id === 'critical-infrastructure').style.opacity } }
    : selectedPreview;
  const orderedLayers = draft.order.map((id) => allLayers.find((l) => l.id === id)).filter(Boolean);
  const overlays = draft.overlayOrder.map((id) => allLayers.find((l) => l.id === id)).filter(Boolean);
  const moveSetting = (key, index, direction) => setDraft((prev) => {
    const order = [...prev[key]];
    const [id] = order.splice(index, 1);
    order.splice(index + direction, 0, id);
    return { ...prev, [key]: order };
  });

  return (
    <div className="admin-page admin-page--scroll">
      <div className="admin-page__intro">
        <h1 className="admin-title">Map layers</h1>
        <p className="admin-muted">
          Manage built-in modelling layers and infrastructure overlays, or upload additional GeoJSON layers. Each layer shown here becomes a switch in
          the map's Modelling Layer panel, with its own legend.
        </p>
      </div>

      {LOCAL_LAYERS && (
        <div className="admin-notice admin-notice--warning" role="note">
          <span>
            <strong>Local test mode.</strong> Uploading, saving and publishing layers only changes this browser; nothing
            is sent to Supabase. Open the local map at{' '}
            <a href="/dashboard" target="_blank" rel="noreferrer">
              /dashboard
            </a>{' '}
            to see what you publish.
          </span>
          <button
            type="button"
            className="admin-btn admin-btn--small"
            disabled={Boolean(busy)}
            onClick={async () => {
              if (!window.confirm('Throw away the local test layers and start again from the real live layers?')) return;
              await clearLocalLayerState();
              setNotice(null);
              setError(null);
              reload();
            }}
          >
            Start over
          </button>
        </div>
      )}

      {LOCAL_FILTERS && !LOCAL_LAYERS && (
        <div className="admin-notice admin-notice--warning" role="note">
          <span>
            <strong>Local test mode is on for filters only.</strong> Map layers always use Supabase: uploads are stored
            in the project-data bucket and publishing changes the real public map.
          </span>
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

      <div className="admin-live admin-live--layers">
        <div className="admin-live__main">
          <section className="admin-card" aria-labelledby="layers-live-title">
            <h2 id="layers-live-title" className="admin-card__title">
              Live now
            </h2>
            <div className="admin-live__box">
              <div className="admin-live__label">Available modelling layers</div>
              <div className="admin-live__value">
                {liveVersion
                  ? liveVersion.name
                    ? `"${liveVersion.name}" (layer version ${liveVersion.version_no})`
                    : `Layer version ${liveVersion.version_no}`
                  : 'None published yet'}
              </div>
              <div className="admin-muted">
                {plural(shownLive.length, 'layer')} on the map{shownLive.length ? `: ${shownLive.join(', ')}` : ''}
              </div>
              {liveVersion && (
                <div className="admin-muted">
                  Published {formatDate(liveVersion.created_at)}
                  {liveVersion.created_by ? ` by ${liveVersion.created_by}` : ''}
                </div>
              )}
            </div>
          </section>

          <section className="admin-card" aria-labelledby="layers-title">
            <div className="admin-card__head">
              <h2 id="layers-title" className="admin-card__title">
                Layers
              </h2>
              <span className="admin-toolbar__spacer" />
              <button type="button" className="admin-btn" onClick={() => setUpload({ replacing: null })}>
                + Upload layer
              </button>
            </div>
            <p className="admin-muted">
              Top to bottom is the order of the modelling switches on the map. Switch a layer
              off to hide it without removing it. Open a layer to set its symbology and popup.
            </p>
            {draft.layers.length === 0 && <p className="admin-empty admin-muted">No layers uploaded yet.</p>}
            {orderedLayers.map((layer, i) => (
              <LayerCard
                key={layer.id}
                layer={layer}
                index={i}
                total={orderedLayers.length}
                liveLayer={liveById.get(layer.id)}
                expanded={expandedId === layer.id}
                onToggle={() => setExpandedId((prev) => (prev === layer.id ? null : layer.id))}
                onChange={(next) => updateLayer(layer.id, next)}
                onMove={(index, direction) => moveSetting('order', index, direction)}
                onRemove={() => removeLayer(layer)}
                onReplace={() => setUpload({ replacing: layer })}
                loadGeojson={loadGeojson}
              />
            ))}
          <h3 className="admin-card__title">Critical Infrastructure overlays</h3>
          <p className="admin-muted">These overlays appear when Critical Infrastructure is selected. Each overlay can be hidden and styled separately.</p>
          {overlays.map((layer, i) => <LayerCard
            key={layer.id} layer={layer} index={i} total={overlays.length}
            liveLayer={liveById.get(layer.id)} expanded={expandedId === layer.id}
            onToggle={() => setExpandedId((id) => id === layer.id ? null : layer.id)}
            onChange={(next) => updateLayer(layer.id, next)}
            onMove={(index, direction) => moveSetting('overlayOrder', index, direction)} loadGeojson={loadGeojson}
          />)}
          </section>

          <div className="admin-savebar" role="region" aria-label="Layer changes">
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
              onClick={() => act(save, 'Layer draft saved.')}
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
              Publish layers…
            </button>
          </div>

          <section className="admin-card" aria-labelledby="layer-history-title">
            <div className="admin-card__head">
              <h2 id="layer-history-title" className="admin-card__title">
                Layer history
              </h2>
              <span className="admin-toolbar__spacer" />
              <button type="button" className="admin-btn admin-btn--small" onClick={handleReset} disabled={Boolean(busy)}>
                Reset draft to the live layers
              </button>
            </div>
            <p className="admin-muted">
              Every published set of layers is kept, with the data it was published with. <strong>Make live</strong>{' '}
              puts one straight back on the map; <strong>Restore to draft</strong> loads it here to edit first.
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
                            aria-label={`Make layer version ${v.version_no} live`}
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
                          aria-label={`Delete layer version ${v.version_no}`}
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
                      Nothing published yet. The map shows only its built-in modelling layers until the first publish.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </section>
        </div>

        <Preview layer={previewLayer} loadGeojson={loadGeojson} showMap={showPreviewMap} />
      </div>

      {upload && (
        <UploadDialog
          replacing={upload.replacing}
          usedLabels={usedLabels}
          onUploaded={handleUploaded}
          onClose={() => setUpload(null)}
        />
      )}
      {publishing && (
        <PublishLayersDialog
          changes={changes}
          firstPublish={!liveVersion}
          onClose={() => setPublishing(false)}
          onPublished={setNotice}
        />
      )}
    </div>
  );
}
