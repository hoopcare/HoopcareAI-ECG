const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function loadDemo() {
  const elements = new Map();
  class Element {
    constructor() { this.children = []; this.events = {}; this.attrs = {}; this.value = ''; this.style = {}; }
    set id(value) { this._id = value; elements.set(value, this); }
    get id() { return this._id; }
    append(...children) { this.children.push(...children); }
    setAttribute(key, value) { this.attrs[key] = value; }
    addEventListener(name, listener) { this.events[name] = listener; }
  }
  const buttons = ['baseline', 'higher'].map(name => {
    const button = new Element();
    button.dataset = { preset: name };
    return button;
  });
  for (const id of ['components', 'error', 'score', 'score-bar', 'diagnostic', 'high5']) {
    const element = new Element();
    element.id = id;
  }
  const document = {
    getElementById: id => elements.get(id),
    createElement: () => new Element(),
    querySelectorAll: () => buttons
  };
  const context = vm.createContext({ document });
  for (const name of ['score.js', 'app.js']) {
    const filename = path.join(__dirname, '../demo', name);
    vm.runInContext(fs.readFileSync(filename, 'utf8'), context, { filename });
  }
  return { elements, buttons };
}

test('UI initializes a labelled, synthetic example and recalculates presets', () => {
  const { elements, buttons } = loadDemo();
  assert.equal(elements.get('components').children.length, 5);
  assert.equal(elements.get('score').textContent, '0.321');
  assert.equal(elements.get('diagnostic').textContent, 'Not reached');
  assert.equal(elements.get('error').hidden, true);
  buttons[1].events.click();
  assert.equal(elements.get('score').textContent, '0.539');
  assert.equal(elements.get('diagnostic').textContent, 'Reached');
  assert.equal(elements.get('high5').textContent, 'Not reached');
  buttons[0].events.click();
  assert.equal(elements.get('score').textContent, '0.321');
});

test('editing scores updates flags and invalid or empty inputs clear stale results', () => {
  const { elements } = loadDemo();
  const input = elements.get('component-0');
  input.value = '1';
  input.events.input();
  assert.equal(elements.get('score').textContent, '1.000');
  assert.equal(elements.get('high5').textContent, 'Reached');
  for (const invalid of ['', '1.1', '-0.1', 'NaN']) {
    input.value = invalid;
    input.events.input();
    assert.equal(input.attrs['aria-invalid'], 'true');
    assert.equal(elements.get('score').textContent, '—');
    assert.equal(elements.get('diagnostic').textContent, 'Unavailable');
    assert.equal(elements.get('error').hidden, false);
    assert.match(elements.get('error').textContent, /between 0 and 1/);
  }
  input.value = '0.1';
  input.events.input();
  assert.equal(input.attrs['aria-invalid'], 'false');
  assert.equal(elements.get('error').hidden, true);
  let prevented = false;
  elements.get('components').events.submit({ preventDefault: () => { prevented = true; } });
  assert.equal(prevented, true);
});
