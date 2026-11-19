'use strict';
const { evaluate, componentLabels } = globalThis.HoopcareScore;
const presets = Object.freeze({
  baseline: Object.freeze([0.1, 0.12, 0.08, 0.04, 0.03]),
  higher: Object.freeze([0.35, 0.18, 0.08, 0.04, 0.02])
});
const form = document.getElementById('components');
const controls = componentLabels.map((label, index) => {
  const row = document.createElement('div');
  row.className = 'input-row';
  const name = document.createElement('label');
  name.htmlFor = `component-${index}`;
  name.textContent = label;
  const input = document.createElement('input');
  Object.assign(input, { id: name.htmlFor, type: 'number', min: '0', max: '1', step: 'any', required: true });
  input.setAttribute('inputmode', 'decimal');
  const meter = document.createElement('meter');
  Object.assign(meter, { min: 0, max: 1, value: 0 });
  meter.setAttribute('aria-hidden', 'true');
  row.append(name, input, meter);
  form.append(row);
  input.addEventListener('input', render);
  return { input, meter };
});

function render() {
  const error = document.getElementById('error');
  try {
    const scores = controls.map(({ input, meter }) => {
      const value = input.value.trim() === '' ? NaN : Number(input.value);
      const valid = Number.isFinite(value) && value >= 0 && value <= 1;
      input.setAttribute('aria-invalid', String(!valid));
      meter.value = valid ? value : 0;
      return value;
    });
    const result = evaluate(scores);
    document.getElementById('score').textContent = result.score.toFixed(3);
    document.getElementById('score-bar').style.width = `${result.score * 100}%`;
    document.getElementById('diagnostic').textContent = result.flags.diagnostic ? 'Reached' : 'Not reached';
    document.getElementById('high5').textContent = result.flags.originalSurgicalHigh5 ? 'Reached' : 'Not reached';
    error.hidden = true;
  } catch (issue) {
    document.getElementById('score').textContent = '—';
    document.getElementById('score-bar').style.width = '0%';
    document.getElementById('diagnostic').textContent = 'Unavailable';
    document.getElementById('high5').textContent = 'Unavailable';
    error.textContent = issue.message;
    error.hidden = false;
  }
}

function applyPreset(name) {
  controls.forEach(({ input }, index) => { input.value = String(presets[name][index]); });
  render();
}

form.addEventListener('submit', event => event.preventDefault());
document.querySelectorAll('[data-preset]').forEach(button => {
  button.addEventListener('click', () => applyPreset(button.dataset.preset));
});
applyPreset('baseline');
