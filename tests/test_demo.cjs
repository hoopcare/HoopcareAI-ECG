const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { evaluate, componentLabels, thresholds } = require('../demo/score.js');

test('five supplied scores combine by the complement of their product', () => {
  const input = Object.freeze([0.1, 0.2, 0.3, 0.4, 0.5]);
  const output = evaluate(input);
  assert.ok(Math.abs(output.score - 0.8488) < 1e-12);
  assert.deepEqual(input, [0.1, 0.2, 0.3, 0.4, 0.5]);
  assert.notEqual(output.components, input);
});

test('zero and one inputs preserve the mathematical limits', () => {
  assert.equal(evaluate([0, 0, 0, 0, 0]).score, 0);
  assert.equal(evaluate([0.2, 1, 0, 0, 0]).score, 1);
  assert.equal(componentLabels.length, 5);
});

test('flags include their exact threshold and exclude values below it', () => {
  for (const [flag, threshold] of Object.entries(thresholds)) {
    assert.equal(evaluate([threshold, 0, 0, 0, 0]).flags[flag], true);
    assert.equal(evaluate([threshold - 1e-8, 0, 0, 0, 0]).flags[flag], false);
  }
  assert.equal(evaluate([0.5, 0, 0, 0, 0]).flags.diagnostic, true);
  assert.equal(evaluate([0.5, 0, 0, 0, 0]).flags.originalSurgicalHigh5, false);
});

test('invalid shape, missing inputs and out-of-range values fail visibly', () => {
  for (const input of [null, {}, [], [0, 0, 0, 0], [0, 0, 0, 0, 0, 0]]) {
    assert.throws(() => evaluate(input), /five/);
  }
  for (const bad of [NaN, Infinity, -Infinity, -0.001, 1.001, '0.1', undefined, null]) {
    assert.throws(() => evaluate([bad, 0, 0, 0, 0]), /between 0 and 1/);
  }
  assert.throws(() => evaluate(Array(5)), /between 0 and 1/);
});

test('larger component scores never reduce the composite', () => {
  const initial = [0.1, 0.2, 0.3, 0.4, 0.5];
  const baseline = evaluate(initial).score;
  initial.forEach((_, index) => {
    const higher = initial.map((value, i) => i === index ? value + 0.01 : value);
    assert.ok(evaluate(higher).score >= baseline);
  });
});

test('demo has no external assets, network requests or local storage', () => {
  for (const name of ['index.html', 'score.js', 'app.js', 'style.css']) {
    const content = fs.readFileSync(path.join(__dirname, '../demo', name), 'utf8');
    assert.doesNotMatch(content, /https?:\/\/|fetch\s*\(|XMLHttpRequest|localStorage|sessionStorage|document\.cookie|WebSocket/);
  }
  const html = fs.readFileSync(path.join(__dirname, '../demo/index.html'), 'utf8');
  assert.match(html, /not ECG interpretation/);
  assert.match(html, /synthetic/i);
  assert.doesNotMatch(html, /type=["']file/);
});
