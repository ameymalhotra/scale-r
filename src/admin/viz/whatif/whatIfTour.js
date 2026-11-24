// Guided tour for the Flood What-If view (D-215): one step at a time, the part being explained is
// highlighted and a small box says what it does. Plain DOM, no packages. The view supplies the steps.

const PAD = 6;      // space between the highlight and the element
const GAP = 12;     // space between the highlight and the text box
const EDGE = 8;     // keep the text box this far inside the window

/**
 * Where to put the text box next to a highlighted element. Pure, so it is tested without a page.
 * Tries right, below, above, then left of the element; with no element (or no room) it is centred.
 * rect and the result are in window pixels.
 */
export function placeBubble(rect, box, view) {
  const clampX = (x) => Math.min(Math.max(x, EDGE), view.w - box.w - EDGE);
  const clampY = (y) => Math.min(Math.max(y, EDGE), view.h - box.h - EDGE);
  if (!rect) return { side: 'center', left: Math.round((view.w - box.w) / 2), top: Math.round((view.h - box.h) / 2) };
  const r = { left: rect.left - PAD, top: rect.top - PAD, right: rect.right + PAD, bottom: rect.bottom + PAD };
  if (r.right + GAP + box.w + EDGE <= view.w) return { side: 'right', left: r.right + GAP, top: clampY(r.top) };
  if (r.bottom + GAP + box.h + EDGE <= view.h) return { side: 'below', left: clampX(r.left), top: r.bottom + GAP };
  if (r.top - GAP - box.h >= EDGE) return { side: 'above', left: clampX(r.left), top: r.top - GAP - box.h };
  if (r.left - GAP - box.w >= EDGE) return { side: 'left', left: r.left - GAP - box.w, top: clampY(r.top) };
  return { side: 'center', left: Math.round((view.w - box.w) / 2), top: clampY(view.h - box.h - EDGE) };
}

/** The part of an element that can be seen: its box cut to every scrolling box around it. */
function visibleRect(el) {
  let r = el.getBoundingClientRect();
  r = { left: r.left, top: r.top, right: r.right, bottom: r.bottom };
  for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) {
    const o = getComputedStyle(p);
    if (!/(auto|scroll|hidden)/.test(o.overflowY + o.overflowX)) continue;
    const c = p.getBoundingClientRect();
    r = { left: Math.max(r.left, c.left), top: Math.max(r.top, c.top), right: Math.min(r.right, c.right), bottom: Math.min(r.bottom, c.bottom) };
  }
  if (r.right <= r.left || r.bottom <= r.top) return null;
  return { ...r, width: r.right - r.left, height: r.bottom - r.top };
}

/**
 * steps: [{ title, text, target?: () => Element | null, before?: async () => void }]
 * Returns { start, stop, get step }. onEnd runs once when the tour closes.
 */
export function createTour({ root, steps, onEnd = () => {} }) {
  let i = -1;
  let spot = null; let bubble = null; let busy = false; let token = 0;

  function build() {
    spot = document.createElement('div');
    spot.className = 'tour-spot';
    bubble = document.createElement('div');
    bubble.className = 'tour-bubble';
    bubble.setAttribute('role', 'dialog');
    bubble.setAttribute('aria-live', 'polite');
    bubble.setAttribute('aria-label', 'Tour');
    root.append(spot, bubble);
    bubble.addEventListener('click', onClick);
    window.addEventListener('keydown', onKey);
    window.addEventListener('resize', place);
  }

  function place() {
    if (!bubble || i < 0) return;
    const t = steps[i].target?.();
    const rect = t && t.getClientRects().length ? visibleRect(t) : null;
    const view = { w: window.innerWidth, h: window.innerHeight };
    const phone = view.w <= 768;
    if (rect) {
      Object.assign(spot.style, { display: 'block', left: `${rect.left - PAD}px`, top: `${rect.top - PAD}px`, width: `${rect.width + 2 * PAD}px`, height: `${rect.height + 2 * PAD}px` });
      spot.classList.remove('none');
    } else {
      Object.assign(spot.style, { display: 'block', left: '50%', top: '50%', width: '0px', height: '0px' });
      spot.classList.add('none');
    }
    if (phone) {
      // on a phone the box sits at the bottom of the screen, or at the top if the highlight is down there
      const low = rect && rect.top > view.h * 0.55;
      Object.assign(bubble.style, { left: `${EDGE}px`, right: `${EDGE}px`, width: 'auto', top: low ? `${EDGE}px` : 'auto', bottom: low ? 'auto' : `${EDGE}px` });
      return;
    }
    Object.assign(bubble.style, { right: 'auto', bottom: 'auto', width: '' });
    const b = bubble.getBoundingClientRect();
    const p = placeBubble(rect, { w: b.width, h: b.height }, view);
    Object.assign(bubble.style, { left: `${p.left}px`, top: `${p.top}px` });
  }

  function render() {
    const s = steps[i];
    const last = i === steps.length - 1;
    bubble.innerHTML = `
      <div class="tour-count">Step ${i + 1} of ${steps.length}</div>
      <h2 class="tour-title">${s.title}</h2>
      <p class="tour-text">${s.text}</p>
      <div class="tour-btns">
        <button type="button" class="linkbtn" data-tour="stop">${last ? 'Close' : 'Skip tour'}</button>
        <span class="tour-gap"></span>
        ${i > 0 ? '<button type="button" class="btn small" data-tour="back">Back</button>' : ''}
        <button type="button" class="btn small primary" data-tour="next">${last ? 'Finish' : 'Next'}</button>
      </div>`;
    // bring the part into view inside the side column (it scrolls on a phone), then highlight what shows
    steps[i].target?.()?.scrollIntoView?.({ block: 'nearest' });
    place();
    bubble.querySelector('[data-tour="next"]').focus({ preventScroll: true });
  }

  async function go(n) {
    if (busy || n < 0 || n >= steps.length) return;
    busy = true;
    const mine = ++token;
    i = n;
    bubble.classList.add('busy');
    try { await steps[i].before?.(); } catch { /* a step that cannot set itself up still shows its text */ }
    busy = false;
    if (mine !== token || !bubble) return;
    bubble.classList.remove('busy');
    render();
    // the map and the side column can still be settling (a card opening, the map sliding): place again
    setTimeout(place, 350);
    setTimeout(place, 900);
  }

  function onClick(e) {
    const a = e.target.closest('[data-tour]')?.dataset.tour;
    if (a === 'next') { if (i === steps.length - 1) stop(); else go(i + 1); }
    else if (a === 'back') go(i - 1);
    else if (a === 'stop') stop();
  }

  function onKey(e) {
    if (e.key === 'Escape') stop();
    else if (e.key === 'ArrowRight' && !e.target.closest?.('input')) go(i + 1);
    else if (e.key === 'ArrowLeft' && !e.target.closest?.('input')) go(i - 1);
  }

  function start() { if (!bubble) build(); go(0); }

  function stop() {
    if (!bubble) return;
    token += 1;
    window.removeEventListener('keydown', onKey);
    window.removeEventListener('resize', place);
    spot.remove(); bubble.remove();
    spot = null; bubble = null; i = -1; busy = false;
    onEnd();
  }

  return { start, stop, get step() { return i; }, get open() { return !!bubble; } };
}
