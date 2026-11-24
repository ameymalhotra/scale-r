// @vitest-environment node
import { describe, expect, it } from 'vitest';
import { moneyShort, shortSentence, stormList } from './whatIfExplain.js';

// Plain wording on the main screen (D-208): rounded dollars and one-line answers.
describe('what-if wording', () => {
  it('rounds money for the main screen', () => {
    expect(moneyShort(1264512)).toBe('$1.3M');
    expect(moneyShort(12345678)).toBe('$12M');
    expect(moneyShort(12231)).toBe('$12k');
    expect(moneyShort(8585)).toBe('$8.6k');
    expect(moneyShort(854)).toBe('$850');
    expect(moneyShort(-8007)).toBe('-$8.0k');
    expect(moneyShort(NaN)).toBe('n/a');
  });

  it('lists storms in plain words', () => {
    expect(stormList(['p10', 'p04', 'p02'])).toBe('the 10, 25 and 50-year storms');
    expect(stormList(['p01'])).toBe('the 100-year storm');
    expect(stormList([])).toBe('');
  });

  it('gives a one-line answer for each reason', () => {
    const storm = (ev, wet, blocked) => ({ ev, wet, blocked });
    const ex = { storms: [storm('p10', false, true), storm('p04', true, true), storm('p02', true, true), storm('p01', true, false), storm('p002', true, false)] };
    expect(shortSentence('protected', null, ex)).toBe('Protected: the wall blocks the 25 and 50-year storms here.');
    expect(shortSentence('inner_water', { name: 'Indian Creek' }, ex)).toBe('Not protected: water reaches it through Indian Creek.');
    expect(shortSentence('overtopped', null, ex)).toMatch(/^Not protected/);
    expect(shortSentence('rain_only', null, ex)).toMatch(/cannot help/);
  });
});
