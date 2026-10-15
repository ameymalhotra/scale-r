import React from 'react';
import { builtinDefinition } from '../layers/builtinRegistry.js';
import { LAYER_SYMBOLS } from '../layers/layerSymbols.js';

export default function BuiltinLayerEditor({ layer, onChange }) {
  const definition = builtinDefinition(layer.id);
  const patch = (change) => onChange({ ...layer, ...change });
  const style = (change) => patch({ style: { ...layer.style, ...change } });
  const symbology = (change) => patch({ symbology: { ...layer.symbology, ...change } });
  const number = (label, key, min, max, step) => (
    <label className="admin-field admin-field--inline">
      <span>{label}</span>
      <input type="number" min={min} max={max} step={step} value={layer.style[key]} onChange={(e) => {
        if (e.target.value !== '') style({ [key]: Math.min(max, Math.max(min, Number(e.target.value))) });
      }} />
    </label>
  );
  return (
    <div className="admin-fc__body">
      <div className="admin-layer-row">
        <label className="admin-field admin-fc__name"><span>Layer name</span><input maxLength={60} value={layer.label} onChange={(e) => patch({ label: e.target.value })} /></label>
        <label className="admin-field admin-layer-grow"><span>Description</span><textarea value={layer.description} onChange={(e) => patch({ description: e.target.value })} /></label>
      </div>
      <p className="admin-muted">{definition.description || 'The source and scientific classification are fixed. Published settings control presentation.'}</p>
      {!definition.group && <fieldset className="admin-layer-section">
        <legend>Colors and legend</legend>
        {layer.symbology.categories.length ? <table className="admin-table admin-fc__options">
          <thead><tr><th scope="col">Source class</th><th scope="col">Color</th><th scope="col">Label in legend</th></tr></thead>
          <tbody>{layer.symbology.categories.map((category, i) => <tr key={category.value}>
            <td>{category.value}</td>
            <td><input type="color" aria-label={`${category.value} color`} value={category.color} onChange={(e) => symbology({ categories: layer.symbology.categories.map((c, j) => j === i ? { ...c, color: e.target.value } : c) })} /></td>
            <td><input aria-label={`${category.value} legend label`} value={category.label || ''} onChange={(e) => symbology({ categories: layer.symbology.categories.map((c, j) => j === i ? { ...c, label: e.target.value } : c) })} /></td>
          </tr>)}</tbody>
        </table> : <label className="admin-field admin-field--inline"><span>Color</span><input type="color" value={layer.symbology.color} onChange={(e) => symbology({ color: e.target.value })} /></label>}
        {!layer.symbology.categories.length && <label className="admin-field"><span>Label in legend</span><input value={layer.symbology.label} placeholder={layer.label} onChange={(e) => symbology({ label: e.target.value })} /></label>}
        {layer.symbology.categories.length > 0 && <label className="admin-field admin-field--inline"><span>NoData / unclassified color</span><input type="color" value={layer.symbology.otherColor} onChange={(e) => symbology({ otherColor: e.target.value })} /></label>}
      </fieldset>}
      <fieldset className="admin-layer-section">
        <legend>Style</legend>
        <div className="admin-layer-row">
          {number('Opacity', 'opacity', 0, 1, 0.05)}
          {!definition.group && <>
            {layer.geometry === 'line' && number('Line width (px)', 'lineWidth', 0.5, 20, 0.5)}
            {layer.geometry === 'point' && <>
              {number('Symbol size (px)', 'pointSize', 4, 48, 1)}
              <label className="admin-field"><span>Point symbol</span><select value={layer.style.symbol} onChange={(e) => style({ symbol: e.target.value })}>{LAYER_SYMBOLS.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}</select></label>
            </>}
            <label className="admin-field admin-field--inline"><span>Outline color</span><input type="color" value={layer.style.outlineColor} onChange={(e) => style({ outlineColor: e.target.value })} /></label>
            {number('Outline width (px)', 'outlineWidth', 0, 10, 0.5)}
          </>}
        </div>
      </fieldset>
      {!definition.group && <fieldset className="admin-layer-section">
        <legend>Popup when a feature is clicked</legend>
        <label className="admin-field"><span>Popup title attribute</span><select value={layer.popup.titleField} onChange={(e) => patch({ popup: { ...layer.popup, titleField: e.target.value } })}>
          <option value="">Layer name</option>{layer.fields.map((f) => <option key={f.name} value={f.name}>{f.name}</option>)}
        </select></label>
        <div className="admin-layer-fields" role="group" aria-label="Attributes shown in popup">
          {layer.fields.filter((f) => f.name !== '__resilienceColorStop').map((f) => <label key={f.name} className="admin-check">
            <input type="checkbox" checked={layer.popup.fields.includes(f.name)} onChange={(e) => patch({ popup: { ...layer.popup, fields: e.target.checked ? [...layer.popup.fields, f.name] : layer.popup.fields.filter((name) => name !== f.name) } })} />{f.name}
          </label>)}
        </div>
      </fieldset>}
    </div>
  );
}
