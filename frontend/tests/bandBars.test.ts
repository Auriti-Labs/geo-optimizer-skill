import assert from 'node:assert/strict';
import { test } from 'node:test';

import { BAND_COLORS, FALLBACK_COLOR, bandBars } from '../src/lib/bandBars.ts';

test('every band keeps its own colour and the printed value is the share', () => {
  const bars = bandBars([['Excellent', 4.1], ['Good', 48.9], ['Foundation', 39.7], ['Critical', 7.3]]);
  assert.deepEqual(bars.map((b) => b.color), Object.values(BAND_COLORS));
  assert.deepEqual(bars.map((b) => b.pct), [4.1, 48.9, 39.7, 7.3]);
});

test('colour follows the band, not its position', () => {
  const [first] = bandBars([['Critical', 10], ['Good', 50]]);
  assert.equal(first.color, BAND_COLORS.Critical);
});

test('tiny, negative, huge and invalid shares stay drawable and honest', () => {
  const bars = bandBars([['Good', 0.2], ['Critical', -5], ['Excellent', 140], ['Foundation', Number.NaN]]);
  assert.deepEqual(bars.map((b) => b.pct), [0.2, 0, 100, 0]);
  assert.ok(bars.every((b) => b.widthPct >= 0.7));
  assert.equal(bars[2].widthPct, 100);
});

test('an unknown band falls back to the default colour', () => {
  assert.equal(bandBars([['Other', 5]])[0].color, FALLBACK_COLOR);
});
