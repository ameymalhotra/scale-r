// @vitest-environment node
import { describe, expect, it } from 'vitest';
import { placeBubble } from './whatIfTour.js';

// The tour's text box must sit next to what it explains and never leave the window (D-215).
describe('tour text box placement', () => {
  const view = { w: 1400, h: 860 };
  const box = { w: 300, h: 180 };
  const inside = (p) => p.left >= 8 && p.top >= 8 && p.left + box.w <= view.w - 8 && p.top + box.h <= view.h - 8;

  it('goes to the right of the side column', () => {
    const p = placeBubble({ left: 14, top: 170, right: 364, bottom: 470 }, box, view);
    expect(p.side).toBe('right');
    expect(p.left).toBeGreaterThan(364);
    expect(inside(p)).toBe(true);
  });

  it('goes above an element at the bottom right corner', () => {
    const p = placeBubble({ left: 1240, top: 700, right: 1390, bottom: 840 }, box, view);
    expect(p.side).toBe('above');
    expect(inside(p)).toBe(true);
  });

  it('is centred when there is nothing to point at', () => {
    expect(placeBubble(null, box, view)).toEqual({ side: 'center', left: 550, top: 340 });
  });

  it('stays inside the window for an element as big as the window', () => {
    const p = placeBubble({ left: 0, top: 0, right: 1400, bottom: 860 }, box, view);
    expect(inside(p)).toBe(true);
  });
});
