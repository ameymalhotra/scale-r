/**
 * Plain-language explanation cards for the Flood What-If view (D-204). Pure functions: they turn engine output
 * (whatIfEngine.seawallReasons, explainBuilding) into HTML; no map or network code here.
 */
import { fromUtm17 } from './whatIfEngine.js';

export const REASON_STYLE = {
  protected: { color: '#1a7f4b', label: 'Protected: behind the wall, and the wall blocks at least one storm that floods it' },
  overtopped: { color: '#e0a100', label: 'Behind the wall, but every storm that floods it goes over the wall' },
  inner_water: { color: '#3b6fb6', label: 'Not behind the wall: nearest water is a canal, creek or inner waterway' },
  bay_beyond_ends: { color: '#8fa3b8', label: 'Not behind the wall: nearest water is the bay beyond the ends of the wall' },
  beyond_1km: { color: '#c4c4c4', label: 'Beyond the 1 km limit' },
  rain_only: { color: '#2aa198', label: 'Floods only from rainfall or canals (C-8/C-9), which a seawall does not change' },
};

const STORM_NAMES = { p10: '10-year', p04: '25-year', p02: '50-year', p01: '100-year', p002: '500-year' };
const TYPES = [['RES1', 'Single-family home'], ['RES2', 'Mobile home'], ['RES3', 'Apartment or condo building'], ['RES4', 'Hotel or motel'],
  ['RES5', 'Dormitory or institution'], ['RES6', 'Nursing home'], ['COM', 'Commercial building'], ['IND', 'Industrial building'],
  ['AGR', 'Agricultural building'], ['REL', 'Place of worship'], ['GOV', 'Government building'], ['EDU', 'School or college']];

const fmt = (n) => (n == null || Number.isNaN(n) ? 'n/a' : Math.round(n).toLocaleString('en-US'));
const ft = (v) => (v == null || !Number.isFinite(v) ? 'none' : `${v.toFixed(1)} ft`);
function money(v) {
  if (v == null || Number.isNaN(v)) return 'n/a';
  const a = Math.abs(v);
  if (a >= 1e6) return `$${(v / 1e6).toFixed(2)}M`;
  return `$${Math.round(v).toLocaleString('en-US')}`;
}
const esc = (t) => String(t).replace(/[&<>"]/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch]));

export function buildingType(occ) {
  const hit = TYPES.find(([p]) => occ.startsWith(p));
  return hit ? hit[1] : `Building (${occ})`;
}

/** The nearest water of a building: the coastal shoreline or an inner water line, with its point (lon, lat). */
export function nearestWater(tile, i, man) {
  const c = tile.cols;
  const [x0, y0] = tile.origin;
  const inner = c.inner_water[i] < c.shore_dist[i];
  if (inner) {
    const nm = man.lists.water_name?.[c.iw_name[i]] || 'NP';
    const name = nm === 'NP' ? 'an unnamed canal or waterway' : titleCase(nm);
    return { inner: true, name, distM: c.inner_water[i], at: fromUtm17(c.iw_x[i] + x0, c.iw_y[i] + y0) };
  }
  if (!Number.isFinite(c.shore_dist[i])) return { inner: false, name: 'no water within the coastal study', distM: null, at: null };
  return { inner: false, name: 'the bay or ocean (FEMA coastal shoreline)', distM: c.shore_dist[i], at: fromUtm17(c.shore_x[i] + x0, c.shore_y[i] + y0) };
}

function titleCase(s) {
  return s.toLowerCase().replace(/\b([a-z])/g, (m) => m.toUpperCase()).replace(/\bC-(\d)/gi, 'C-$1');
}

export function reasonSentence(reason, water, crestFt) {
  switch (reason) {
    case 'protected': return `Protected: it is behind the wall, and the +${crestFt.toFixed(1)} ft wall keeps out at least one storm that floods it.`;
    case 'overtopped': return `Behind the wall, but every storm that floods it rises above the +${crestFt.toFixed(1)} ft crest (or its ground is higher than the crest), so the wall changes nothing here.`;
    case 'inner_water': return `Not protected: its nearest water is ${water.name}, ${fmt(water.distM)} m away, so a storm reaches it around the wall.`;
    case 'bay_beyond_ends': return 'Not protected: its nearest water is the bay beyond the ends of the wall, so the wall does not stand between it and the water.';
    case 'beyond_1km': return 'Not counted: it is more than 1 km from the wall, beyond the safety limit.';
    case 'rain_only': return 'A seawall cannot help: it floods only from rainfall or canals (C-8/C-9 model or the FEMA map level), not from the sea.';
    default: return '';
  }
}

/** Facts shown on a card, as [label, value] pairs (compared between two cards). */
export function facts(tile, i, man, extra = {}) {
  const c = tile.cols;
  const floor = c.ffe[i] - c.ground[i];
  const water = nearestWater(tile, i, man);
  const out = [
    ['Building type', buildingType(man.lists.occtype[c.occ[i]])],
    ['Year built', c.year_built?.[i] > 0 ? String(Math.round(c.year_built[i])) : 'not known'],
    ['Ground height', `${c.ground[i].toFixed(1)} ft above NAVD88`],
    ['First floor', `${c.ffe[i].toFixed(1)} ft (${floor.toFixed(1)} ft above ground; ${c.ffe_est[i] ? 'estimated' : 'from records'})`],
    ['Building value', `${money(c.val_struct[i])} structure, ${money(c.val_cont[i])} contents`],
    ['Estimated residents', fmt(c.residents[i])],
    ['Nearest water', water.distM == null ? water.name : `${water.name}, ${fmt(water.distM)} m`],
  ];
  if (extra.distWallM != null) out.push(['Distance to the wall', `${fmt(extra.distWallM)} m`]);
  if (extra.rank) out.push(['Rank by expected damage', extra.rank]);
  return out;
}

/**
 * One card. other (optional): the card it is compared with; rows that differ are highlighted.
 * card: {title, sentence, facts, ex: explainBuilding result, kind: 'seawall' | 'elevation' | 'none'}
 */
export function cardHtml(card, other) {
  const diff = (k, v) => other && other.facts.find(([kk]) => kk === k)?.[1] !== v;
  const factRows = card.facts.map(([k, v]) => `<tr class="${diff(k, v) ? 'diff' : ''}"><th>${esc(k)}</th><td>${esc(v)}</td></tr>`).join('');
  const ex = card.ex;
  const col = card.kind === 'seawall' ? 'Wall blocks it?' : card.kind === 'elevation' ? 'Above the raised floor?' : '';
  const storms = ex.storms.map((s, j) => {
    const o = other?.ex.storms[j];
    const cell3 = card.kind === 'seawall' ? (!s.wet ? 'dry' : s.blocked ? 'yes' : s.overWall ? 'no, goes over' : s.source === 'sea' ? 'no, not behind it' : 'no, not sea water')
      : card.kind === 'elevation' ? (s.aboveFloorAfter ? 'yes' : 'no') : '';
    const d = o && (Math.round(o.lossBefore) !== Math.round(s.lossBefore) || Math.round(o.lossAfter) !== Math.round(s.lossAfter) || (o.level ?? 0).toFixed(1) !== (s.level ?? 0).toFixed(1));
    return `<tr class="${d ? 'diff' : ''}"><td>${STORM_NAMES[s.ev] || s.ev}</td><td>${s.level == null ? 'dry' : `${ft(s.level)}${s.wet ? '' : ' (below ground)'}<br><span class="muted">${s.source}</span>`}</td>
      <td>${s.aboveFloorBefore ? 'yes' : 'no'}</td>${col ? `<td>${cell3}</td>` : ''}<td>${money(s.lossBefore)}${col ? ` → ${money(s.lossAfter)}` : ''}</td></tr>`;
  }).join('');
  const avoided = ex.eydBefore - ex.eydAfter;
  const dsum = other && Math.round(other.ex.eydBefore - other.ex.eydAfter) !== Math.round(avoided);
  return `<article class="card">
    <h3>${esc(card.title)}</h3>
    ${card.sentence ? `<p class="reason" style="border-color:${card.color || '#6b7783'}">${esc(card.sentence)}</p>` : ''}
    <table class="facts">${factRows}</table>
    <table class="storms"><thead><tr><th>Storm</th><th>Water level</th><th>Above floor?</th>${col ? `<th>${col}</th>` : ''}<th>Damage${col ? ' before → after' : ''}</th></tr></thead><tbody>${storms}</tbody></table>
    <p class="sum ${dsum ? 'diff' : ''}">Yearly damage: <b>${money(ex.eydBefore)}</b> before${col ? `, <b>${money(ex.eydAfter)}</b> after, <b>${money(avoided)}</b> avoided` : ''}.</p>
  </article>`;
}
