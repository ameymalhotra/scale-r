/**
 * Plain-language explanation cards for the Flood What-If view (D-204, short layout D-208). Pure functions: they turn
 * engine output (whatIfEngine.seawallReasons, explainBuilding) into text and HTML; no map or network code here.
 */
import { fromUtm17 } from './whatIfEngine.js';

export const REASON_STYLE = {
  protected: { color: '#1a7f4b', short: 'Protected', label: 'Protected: behind the wall, and the wall blocks at least one storm that floods it' },
  overtopped: { color: '#e0a100', short: 'Water goes over the wall', label: 'Behind the wall, but every storm that floods it goes over the wall' },
  inner_water: { color: '#3b6fb6', short: 'Water comes through a canal or creek', label: 'Not behind the wall: nearest water is a canal, creek or inner waterway' },
  bay_beyond_ends: { color: '#8fa3b8', short: 'Water comes around the ends', label: 'Not behind the wall: nearest water is the bay beyond the ends of the wall' },
  beyond_1km: { color: '#c4c4c4', short: 'More than 1 km away', label: 'Beyond the 1 km limit' },
  rain_only: { color: '#2aa198', short: 'Floods from rain, not the sea', label: 'Floods only from rainfall or canals (C-8/C-9), which a seawall does not change' },
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

/** Rounded dollars for the main screen (D-208): $1.3M, $12k, $8.6k, $850. */
export function moneyShort(v) {
  if (v == null || Number.isNaN(v)) return 'n/a';
  const a = Math.abs(v);
  const sg = v < 0 ? '-' : '';
  if (a >= 1e6) return `${sg}$${(a / 1e6).toFixed(a >= 1e7 ? 0 : 1)}M`;
  if (a >= 1e4) return `${sg}$${Math.round(a / 1e3)}k`;
  if (a >= 1e3) return `${sg}$${(a / 1e3).toFixed(1)}k`;
  return `${sg}$${Math.round(a / 10) * 10}`;
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

/** The longer explanation, shown under Details. */
export function reasonSentence(reason, water, crestFt) {
  switch (reason) {
    case 'protected': return `Protected: it is behind the wall, and the +${crestFt.toFixed(1)} ft wall keeps out at least one storm that floods it.`;
    case 'overtopped': return `Behind the wall, but every storm that floods it rises above the +${crestFt.toFixed(1)} ft wall top (or its ground is higher than the wall top), so the wall changes nothing here.`;
    case 'inner_water': return `Not protected: its nearest water is ${water.name}, ${fmt(water.distM)} m away, so a storm reaches it around the wall.`;
    case 'bay_beyond_ends': return 'Not protected: its nearest water is the bay beyond the ends of the wall, so the wall does not stand between it and the water.';
    case 'beyond_1km': return 'Not counted: it is more than 1 km from the wall, beyond the safety limit.';
    case 'rain_only': return 'A seawall cannot help: it floods only from rainfall or canals (C-8/C-9 model or the FEMA map level), not from the sea.';
    default: return '';
  }
}

/** "the 10, 25 and 50-year storms" from storm keys. */
export function stormList(evs) {
  const n = evs.map((e) => (STORM_NAMES[e] || e).replace('-year', ''));
  if (!n.length) return '';
  if (n.length === 1) return `the ${n[0]}-year storm`;
  return `the ${n.slice(0, -1).join(', ')} and ${n[n.length - 1]}-year storms`;
}

/** One-line answer at the top of a building card (D-208). */
export function shortSentence(reason, water, ex) {
  switch (reason) {
    case 'protected': {
      const evs = ex.storms.filter((s) => s.wet && s.blocked).map((s) => s.ev);
      return evs.length ? `Protected: the wall blocks ${stormList(evs)} here.` : 'Protected: the wall lowers the flooding here.';
    }
    case 'overtopped': return 'Not protected: the water that floods it goes over the wall.';
    case 'inner_water': return `Not protected: water reaches it through ${water.name}.`;
    case 'bay_beyond_ends': return 'Not protected: water reaches it around the ends of the wall.';
    case 'beyond_1km': return 'Not counted: it is more than 1 km from the wall.';
    case 'rain_only': return 'A seawall cannot help: it floods from rain or canals, not the sea.';
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
    ['Ground height', `${c.ground[i].toFixed(1)} ft`],
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
 * One card, short layout (D-208): the answer, damage before, after and avoided, and the rest under Details.
 * other (optional): the card it is compared with; values that differ are highlighted.
 * card: {title, sentence, why, facts, ex: explainBuilding result, kind: 'seawall' | 'elevation' | 'none', behind, color}
 */
export function cardHtml(card, other) {
  const diff = (k, v) => other && other.facts.find(([kk]) => kk === k)?.[1] !== v;
  const factRows = card.facts.map(([k, v]) => `<tr class="${diff(k, v) ? 'diff' : ''}"><th>${esc(k)}</th><td>${esc(v)}</td></tr>`).join('');
  const ex = card.ex;
  const col = card.kind === 'seawall' ? 'Wall blocks it?' : card.kind === 'elevation' ? 'Above the raised floor?' : '';
  const storms = ex.storms.map((s, j) => {
    const o = other?.ex.storms[j];
    const cell3 = card.kind === 'seawall' ? (!s.wet ? 'dry' : s.source !== 'sea' ? 'no, not sea water' : !card.behind ? 'no, not behind it' : s.blocked ? 'yes' : 'no, goes over')
      : card.kind === 'elevation' ? (s.aboveFloorAfter ? 'yes' : 'no') : '';
    const d = o && (Math.round(o.lossBefore) !== Math.round(s.lossBefore) || Math.round(o.lossAfter) !== Math.round(s.lossAfter) || (o.level ?? 0).toFixed(1) !== (s.level ?? 0).toFixed(1));
    return `<tr class="${d ? 'diff' : ''}"><td>${STORM_NAMES[s.ev] || s.ev}</td><td>${s.level == null ? 'dry' : `${ft(s.level)}${s.wet ? '' : ' (below ground)'}<br><span class="muted">${s.source}</span>`}</td>
      <td>${s.aboveFloorBefore ? 'yes' : 'no'}</td>${col ? `<td>${cell3}</td>` : ''}<td>${money(s.lossBefore)}${col ? ` → ${money(s.lossAfter)}` : ''}</td></tr>`;
  }).join('');
  // a building with several uses shows its totals; the uses are listed below (D-218)
  const tot = card.total || { before: ex.eydBefore, after: ex.eydAfter };
  const avoided = tot.before - tot.after;
  const oAv = other ? other.ex.eydBefore - other.ex.eydAfter : null;
  const dd = (a, b) => (other && Math.round(a) !== Math.round(b) ? 'diff' : '');
  const nums = col
    ? `<div class="nums"><div class="${dd(tot.before, other?.ex.eydBefore)}"><span class="n">${moneyShort(tot.before)}</span><span class="l">a year before</span></div>
        <div class="${dd(tot.after, other?.ex.eydAfter)}"><span class="n">${moneyShort(tot.after)}</span><span class="l">after</span></div>
        <div class="av ${dd(avoided, oAv)}"><span class="n">${moneyShort(avoided)}</span><span class="l">avoided</span></div></div>`
    : `<div class="nums"><div class="${dd(tot.before, other?.ex.eydBefore)}"><span class="n">${moneyShort(tot.before)}</span><span class="l">flood damage a year today</span></div></div>`;
  const uses = card.uses ? `<table class="uses"><caption>Uses in this building</caption><thead><tr><th>Use</th><th>Damage a year${col ? ' before → after' : ''}</th></tr></thead><tbody>${
    card.uses.map((u) => `<tr><td>${esc(u.label)} <span class="muted">${esc(u.code)}</span></td><td>${money(u.before)}${col ? ` → ${money(u.after)}` : ''}</td></tr>`).join('')}</tbody></table>` : '';
  return `<article class="card">
    <h3>${esc(card.title)}</h3>
    ${card.sentence ? `<p class="reason" style="border-color:${card.color || '#6b7783'}">${esc(card.sentence)}</p>` : ''}
    ${nums}
    ${uses}
    <details class="more"><summary>Details</summary>
      ${card.uses ? '<p class="muted">The national structure inventory lists each use of this building as its own record. The storm table and facts below are for the first use.</p>' : ''}
      ${card.why ? `<p class="why">${esc(card.why)}</p>` : ''}
      <table class="storms"><thead><tr><th>Storm</th><th>Water level</th><th>Above floor?</th>${col ? `<th>${col}</th>` : ''}<th>Damage${col ? ' before → after' : ''}</th></tr></thead><tbody>${storms}</tbody></table>
      <table class="facts">${factRows}</table>
      <p class="muted">Heights in feet above NAVD88, the standard US land datum. Yearly damage averages the five storms by how often each happens.</p>
    </details>
  </article>`;
}
