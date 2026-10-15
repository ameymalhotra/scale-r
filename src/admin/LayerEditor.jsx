import React, { useLayoutEffect, useRef, useState } from 'react';
import {
  CLASS_METHODS,
  COLOR_RAMPS,
  MAX_CATEGORIES,
  MAX_CLASSES,
  METHOD_LABELS,
  MODE_LABELS,
  SYMBOLOGY_MODES,
  buildCategories,
  categoryColor,
  classLabel,
  colorClasses,
  computeClasses,
  numericValues,
  rampColors,
  uniqueValues,
} from '../layers/layerConfig.js';
import { LAYER_SYMBOLS } from '../layers/layerSymbols.js';
import { LegendGlyph } from '../layers/LayerLegend.jsx';

const plural = (n, word) => `${n.toLocaleString()} ${word}${n === 1 ? '' : 's'}`;

function SymbolPicker({ value, onChange, color, label }) {
  return (
    <div className="admin-symbols" role="radiogroup" aria-label={label}>
      {LAYER_SYMBOLS.map((s) => (
        <button
          key={s.id}
          type="button"
          role="radio"
          aria-checked={value === s.id}
          aria-label={s.label}
          title={s.label}
          className={`admin-symbols__item${value === s.id ? ' is-selected' : ''}`}
          onClick={() => onChange(s.id)}
        >
          <LegendGlyph kind="point" symbol={s.id} color={color} outlineColor="transparent" size={18} />
        </button>
      ))}
    </div>
  );
}

function SymbolSelect({ value, onChange, label }) {
  return (
    <select aria-label={label} value={value} onChange={(e) => onChange(e.target.value)}>
      {LAYER_SYMBOLS.map((s) => (
        <option key={s.id} value={s.id}>
          {s.label}
        </option>
      ))}
    </select>
  );
}

function NumberField({ label, value, min, max, step, onChange }) {
  return (
    <label className="admin-field admin-field--inline">
      <span>{label}</span>
      <input
        type="number"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(e) => {
          const n = Number(e.target.value);
          if (e.target.value !== '' && Number.isFinite(n)) onChange(n);
        }}
      />
    </label>
  );
}

function ColorField({ label, value, onChange }) {
  return (
    <label className="admin-field admin-field--inline">
      <span>{label}</span>
      <input type="color" value={value} onChange={(e) => onChange(e.target.value)} />
    </label>
  );
}

function CategorizedEditor({ layer, symbology, patch, getSymbology, withData, dataError }) {
  const isPoint = layer.geometry === 'point';
  const [truncated, setTruncated] = useState(false);

  const loadValues = (field, keep) => {
    if (!keep) patch({ field, categories: [] });
    withData((data) => {
      const current = getSymbology();
      if (current.field !== field) return;
      const values = uniqueValues(data, field);
      setTruncated(values.length > MAX_CATEGORIES);
      patch({ categories: buildCategories(values, keep ? current.categories : []) });
    });
  };

  const patchCategory = (i, change) => {
    const categories = symbology.categories.map((c, k) => {
      if (k !== i) return c;
      const next = { ...c, ...change };
      if (next.label === '') delete next.label;
      return next;
    });
    patch({ categories });
  };

  return (
    <>
      <div className="admin-layer-row">
        <label className="admin-field admin-field--inline">
          <span>Attribute</span>
          <select
            aria-label="Attribute to categorize by"
            value={symbology.field}
            onChange={(e) => (e.target.value ? loadValues(e.target.value, false) : patch({ field: '', categories: [] }))}
          >
            <option value="">Choose an attribute…</option>
            {layer.fields.map((f) => (
              <option key={f.name} value={f.name}>
                {f.name}
              </option>
            ))}
          </select>
        </label>
        {symbology.field && (
          <>
            <button type="button" className="admin-btn admin-btn--small" onClick={() => loadValues(symbology.field, true)}>
              Reload values
            </button>
            <button
              type="button"
              className="admin-btn admin-btn--small"
              onClick={() => patch({ categories: symbology.categories.map((c, i) => ({ ...c, color: categoryColor(i) })) })}
            >
              Reset colors
            </button>
          </>
        )}
      </div>
      {dataError && <p className="admin-error">{dataError}</p>}
      {truncated && (
        <p className="admin-warning">
          Only the {MAX_CATEGORIES} most common values get their own color; the rest use the color for other values.
        </p>
      )}
      {symbology.categories.length > 0 && (
        <table className="admin-table admin-fc__options">
          <thead>
            <tr>
              <th scope="col">Value</th>
              <th scope="col">Label in the legend</th>
              <th scope="col">Color</th>
              {isPoint && <th scope="col">Symbol</th>}
            </tr>
          </thead>
          <tbody>
            {symbology.categories.map((c, i) => (
              <tr key={c.value}>
                <td>{c.value}</td>
                <td>
                  <input
                    type="text"
                    aria-label={`Label for ${c.value}`}
                    value={c.label ?? ''}
                    placeholder={c.value}
                    maxLength={80}
                    onChange={(e) => patchCategory(i, { label: e.target.value })}
                  />
                </td>
                <td>
                  <input
                    type="color"
                    aria-label={`Color for ${c.value}`}
                    value={c.color}
                    onChange={(e) => patchCategory(i, { color: e.target.value })}
                  />
                </td>
                {isPoint && (
                  <td>
                    <SymbolSelect
                      label={`Symbol for ${c.value}`}
                      value={c.symbol ?? layer.style.symbol}
                      onChange={(symbol) => patchCategory(i, { symbol })}
                    />
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <div className="admin-layer-row">
        <ColorField label="Other values" value={symbology.otherColor} onChange={(otherColor) => patch({ otherColor })} />
        <label className="admin-check">
          <input
            type="checkbox"
            checked={symbology.showOther}
            onChange={(e) => patch({ showOther: e.target.checked })}
          />
          Show "Other" in the legend
        </label>
      </div>
    </>
  );
}

/** Recomputes a graduated layer's classes from its data, using the symbology as it is when the data arrives. */
function reclassify(patch, getSymbology, withData) {
  const now = getSymbology();
  if (!now.field || now.method === 'manual') return;
  withData((data) => {
    const s = getSymbology();
    if (!s.field || s.method === 'manual') return;
    const ranges = computeClasses(numericValues(data, s.field), s.method, s.classCount);
    patch({ classes: colorClasses(ranges, s.ramp, s.classes) });
  });
}

function GraduatedEditor({ layer, symbology, patch, getSymbology, withData, dataError }) {
  const numberFields = layer.fields.filter((f) => f.type === 'number');

  const classify = (change) => {
    patch(change);
    reclassify(patch, getSymbology, withData);
  };

  const editBreak = (i, value) => {
    const classes = symbology.classes.map((c) => ({ ...c }));
    classes[i].min = value;
    if (i > 0) classes[i - 1].max = value;
    patch({ method: 'manual', classes });
  };

  const editClass = (i, change) => {
    const classes = symbology.classes.map((c, k) => {
      if (k !== i) return c;
      const next = { ...c, ...change };
      if (next.label === '') delete next.label;
      return next;
    });
    patch({ classes });
  };

  return (
    <>
      {numberFields.length === 0 && (
        <p className="admin-warning">This layer has no numeric attributes, so it cannot be graduated.</p>
      )}
      <div className="admin-layer-row">
        <label className="admin-field admin-field--inline">
          <span>Numeric attribute</span>
          <select
            aria-label="Attribute to graduate by"
            value={symbology.field}
            onChange={(e) =>
              classify(
                e.target.value
                  ? { field: e.target.value, method: symbology.method === 'manual' ? 'quantile' : symbology.method }
                  : { field: '', classes: [] },
              )
            }
          >
            <option value="">Choose an attribute…</option>
            {numberFields.map((f) => (
              <option key={f.name} value={f.name}>
                {f.name}
              </option>
            ))}
          </select>
        </label>
        <label className="admin-field admin-field--inline">
          <span>Breaks</span>
          <select aria-label="Class breaks" value={symbology.method} onChange={(e) => classify({ method: e.target.value })}>
            {CLASS_METHODS.map((m) => (
              <option key={m} value={m}>
                {METHOD_LABELS[m]}
              </option>
            ))}
          </select>
        </label>
        <label className="admin-field admin-field--inline">
          <span>Classes</span>
          <select
            aria-label="Number of classes"
            value={symbology.classCount}
            disabled={symbology.method === 'manual'}
            onChange={(e) => classify({ classCount: Number(e.target.value) })}
          >
            {Array.from({ length: MAX_CLASSES - 1 }, (_, i) => i + 2).map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>
        <label className="admin-field admin-field--inline">
          <span>Color ramp</span>
          <select
            aria-label="Color ramp"
            value={symbology.ramp}
            onChange={(e) => patch({ ramp: e.target.value, classes: colorClasses(symbology.classes, e.target.value, symbology.classes) })}
          >
            {Object.entries(COLOR_RAMPS).map(([id, r]) => (
              <option key={id} value={id}>
                {r.label}
              </option>
            ))}
          </select>
        </label>
        <span className="admin-ramp" aria-hidden="true">
          {rampColors(symbology.ramp, 7).map((c) => (
            <i key={c} style={{ background: c }} />
          ))}
        </span>
      </div>
      {dataError && <p className="admin-error">{dataError}</p>}
      {symbology.classes.length > 0 && (
        <table className="admin-table admin-fc__options">
          <thead>
            <tr>
              <th scope="col">From</th>
              <th scope="col">To</th>
              <th scope="col">Color</th>
              <th scope="col">Label in the legend</th>
            </tr>
          </thead>
          <tbody>
            {symbology.classes.map((c, i) => (
              <tr key={i}>
                <td>
                  <input
                    type="number"
                    aria-label={`Class ${i + 1} starts at`}
                    value={c.min}
                    disabled={i === 0}
                    onChange={(e) => e.target.value !== '' && editBreak(i, Number(e.target.value))}
                  />
                </td>
                <td>
                  <input
                    type="number"
                    aria-label={`Class ${i + 1} ends at`}
                    value={c.max}
                    disabled={i < symbology.classes.length - 1}
                    onChange={(e) => e.target.value !== '' && editClass(i, { max: Number(e.target.value) })}
                  />
                </td>
                <td>
                  <input
                    type="color"
                    aria-label={`Color for class ${i + 1}`}
                    value={c.color}
                    onChange={(e) => editClass(i, { color: e.target.value })}
                  />
                </td>
                <td>
                  <input
                    type="text"
                    aria-label={`Label for class ${i + 1}`}
                    value={c.label ?? ''}
                    placeholder={classLabel({ ...c, label: '' })}
                    maxLength={80}
                    onChange={(e) => editClass(i, { label: e.target.value })}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <ColorField label="No value" value={symbology.otherColor} onChange={(otherColor) => patch({ otherColor })} />
    </>
  );
}

/** Name, data, symbology, style and popup settings of one uploaded layer. */
export default function LayerEditor({ layer, onChange, loadGeojson, onReplace }) {
  const [dataError, setDataError] = useState(null);
  const { symbology, style } = layer;
  // Edits that wait for the layer data apply on top of whatever was changed meanwhile.
  const latest = useRef(layer);
  useLayoutEffect(() => {
    latest.current = layer;
  }, [layer]);
  const commit = (change) => {
    latest.current = { ...latest.current, ...change };
    onChange(latest.current);
  };
  const getSymbology = () => latest.current.symbology;
  const patchSymbology = (change) => commit({ symbology: { ...latest.current.symbology, ...change } });
  const patchStyle = (change) => commit({ style: { ...latest.current.style, ...change } });
  const patchPopup = (change) => commit({ popup: { ...latest.current.popup, ...change } });

  const withData = async (fn) => {
    setDataError(null);
    try {
      fn(await loadGeojson(layer.file));
    } catch (e) {
      setDataError(`Could not load the layer data: ${e.message}`);
    }
  };

  const togglePopupField = (name, on) =>
    patchPopup({
      fields: on
        ? layer.fields.map((f) => f.name).filter((n) => n === name || layer.popup.fields.includes(n))
        : layer.popup.fields.filter((n) => n !== name),
    });

  return (
    <div className="admin-fc__body">
      <div className="admin-layer-row">
        <label className="admin-field admin-fc__name">
          <span>Name shown on the map</span>
          <input type="text" value={layer.label} maxLength={60} onChange={(e) => commit({ label: e.target.value })} />
        </label>
        <label className="admin-field admin-layer-grow">
          <span>Description (admin only)</span>
          <input
            type="text"
            value={layer.description}
            maxLength={300}
            onChange={(e) => commit({ description: e.target.value })}
          />
        </label>
      </div>
      <div className="admin-layer-row admin-muted">
        <span>
          {plural(layer.featureCount, 'feature')} · {plural(layer.fields.length, 'attribute')} · <code>{layer.file}</code>
        </span>
        <button type="button" className="admin-btn admin-btn--small" onClick={onReplace}>
          Replace data…
        </button>
      </div>

      <fieldset className="admin-layer-section">
        <legend>Symbology</legend>
        <div className="admin-segmented" role="radiogroup" aria-label="Symbology type">
          {SYMBOLOGY_MODES.map((mode) => (
            <button
              key={mode}
              type="button"
              role="radio"
              aria-checked={symbology.mode === mode}
              className={symbology.mode === mode ? 'is-selected' : undefined}
              onClick={() => {
                setDataError(null);
                const { field } = symbology;
                const fieldType = layer.fields.find((f) => f.name === field)?.type;
                if (mode === 'graduated' && field && fieldType !== 'number') {
                  patchSymbology({ mode, field: '', classes: [] });
                  return;
                }
                patchSymbology({ mode });
                if (mode === 'categorized' && field && !symbology.categories.length) {
                  withData((data) => {
                    const s = getSymbology();
                    if (s.mode === 'categorized' && s.field === field && !s.categories.length) {
                      patchSymbology({ categories: buildCategories(uniqueValues(data, field)) });
                    }
                  });
                } else if (mode === 'graduated' && field && !symbology.classes.length) {
                  reclassify(patchSymbology, getSymbology, withData);
                }
              }}
            >
              {MODE_LABELS[mode]}
            </button>
          ))}
        </div>
        {symbology.mode === 'single' && (
          <>
            <ColorField label="Color" value={symbology.color} onChange={(color) => patchSymbology({ color })} />
            <label className="admin-field"><span>Label in legend</span><input value={symbology.label} placeholder={layer.label} onChange={(e) => patchSymbology({ label: e.target.value })} /></label>
          </>
        )}
        {symbology.mode === 'categorized' && (
          <CategorizedEditor
            layer={layer}
            symbology={symbology}
            patch={patchSymbology}
            getSymbology={getSymbology}
            withData={withData}
            dataError={dataError}
          />
        )}
        {symbology.mode === 'graduated' && (
          <GraduatedEditor
            layer={layer}
            symbology={symbology}
            patch={patchSymbology}
            getSymbology={getSymbology}
            withData={withData}
            dataError={dataError}
          />
        )}
      </fieldset>

      <fieldset className="admin-layer-section">
        <legend>Style</legend>
        <div className="admin-layer-row">
          <label className="admin-field admin-field--inline">
            <span>Opacity {Math.round(style.opacity * 100)}%</span>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={style.opacity}
              onChange={(e) => patchStyle({ opacity: Number(e.target.value) })}
            />
          </label>
          {layer.geometry === 'line' && (
            <NumberField label="Line width (px)" value={style.lineWidth} min={0.5} max={20} step={0.5} onChange={(lineWidth) => patchStyle({ lineWidth })} />
          )}
          {layer.geometry === 'point' && (
            <NumberField label="Symbol size (px)" value={style.pointSize} min={4} max={48} step={1} onChange={(pointSize) => patchStyle({ pointSize })} />
          )}
          {layer.geometry !== 'line' && (
            <>
              <ColorField label="Outline color" value={style.outlineColor} onChange={(outlineColor) => patchStyle({ outlineColor })} />
              <NumberField
                label="Outline width (px)"
                value={style.outlineWidth}
                min={0}
                max={layer.geometry === 'point' ? 3 : 10}
                step={0.5}
                onChange={(outlineWidth) => patchStyle({ outlineWidth })}
              />
            </>
          )}
        </div>
        {layer.geometry === 'point' && (
          <div className="admin-field">
            <span>Symbol{symbology.mode === 'categorized' ? ' (default; each category can override it)' : ''}</span>
            <SymbolPicker
              label="Point symbol"
              value={style.symbol}
              color={symbology.mode === 'single' ? symbology.color : '#34495e'}
              onChange={(symbol) => patchStyle({ symbol })}
            />
          </div>
        )}
      </fieldset>

      <fieldset className="admin-layer-section">
        <legend>Popup when a feature is clicked</legend>
        {layer.fields.length === 0 ? (
          <p className="admin-muted">This layer has no attributes to show.</p>
        ) : (
          <>
            <label className="admin-field admin-field--inline">
              <span>Title</span>
              <select aria-label="Popup title attribute" value={layer.popup.titleField} onChange={(e) => patchPopup({ titleField: e.target.value })}>
                <option value="">The layer name</option>
                {layer.fields.map((f) => (
                  <option key={f.name} value={f.name}>
                    {f.name}
                  </option>
                ))}
              </select>
            </label>
            <div className="admin-layer-fields" role="group" aria-label="Attributes shown in the popup">
              {layer.fields.map((f) => (
                <label key={f.name} className="admin-check">
                  <input
                    type="checkbox"
                    checked={layer.popup.fields.includes(f.name)}
                    onChange={(e) => togglePopupField(f.name, e.target.checked)}
                  />
                  {f.name}
                </label>
              ))}
            </div>
            <p className="admin-muted">No title and no attributes means clicking the layer shows nothing.</p>
          </>
        )}
      </fieldset>
    </div>
  );
}
