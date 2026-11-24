// @vitest-environment node
import { describe, expect, it } from 'vitest';
import { markerList, projectsAfterExamples, setAside, tabChange } from './whatIfTabs.js';

// Regression tests for "examples stay on the map after changing tab" (D-213, D-214).
describe('what-if tabs', () => {
  it('leaves Examples whenever another tab is clicked, or Examples again', () => {
    for (const t of ['seawall', 'elevation']) expect(tabChange('examples', t)).toEqual({ next: t, leaveExamples: true, enterExamples: false });
    expect(tabChange('examples', 'examples')).toEqual({ next: null, leaveExamples: true, enterExamples: false });
  });

  it('enters Examples from any other state, and only then', () => {
    for (const from of [null, 'seawall', 'elevation']) expect(tabChange(from, 'examples')).toEqual({ next: 'examples', leaveExamples: false, enterExamples: true });
    expect(tabChange('seawall', 'elevation')).toEqual({ next: 'elevation', leaveExamples: false, enterExamples: false });
    expect(tabChange('seawall', 'seawall')).toEqual({ next: null, leaveExamples: false, enterExamples: false });
  });

  it('never brings an example back with the user projects', () => {
    const own = { name: 'Seawall 1' };
    const ex = { name: 'Example', example: true };
    const saved = setAside([own, ex], null);
    expect(saved).toEqual([own]);
    expect(setAside([ex], saved)).toBe(saved);
    expect(projectsAfterExamples([own, ex])).toEqual([own]);
    expect(projectsAfterExamples(null)).toEqual([]);
  });

  it('draws exactly one marker per project, and none when there are no projects', () => {
    const at = (p) => p.at;
    expect(markerList([], -1, at)).toEqual([]);
    const ms = markerList([{ name: 'a', at: [1, 2] }, { name: 'b', at: null }, { name: 'c', at: [3, 4] }], 2, at);
    expect(ms.map((m) => [m.num, m.sel])).toEqual([[1, false], [3, true]]);
  });
});
