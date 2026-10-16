/**
 * Exercise the patched passphrase gate by extracting the real `waitAction`
 * source out of lib/splash.js and running it against a stub DOM.
 *
 * This tests the shipped code text, not a re-implementation: if the extraction
 * or the patch drifts, the assertions fail.
 */

import { readFileSync } from 'node:fs';

const FILE = String.raw`%WORKSPACE%\plugins\dsh-startup-screen\lib\splash.js`;
const source = readFileSync(FILE, 'utf8');

const start = source.indexOf('  var HINT_PASS = ');
const end = source.indexOf('  function releaseAll()');
if (start < 0 || end < 0 || end <= start) {
  console.log('FAIL: could not locate the patched waitAction block');
  process.exit(1);
}
const block = source.slice(start, end);
console.log('extracted ' + block.length + ' chars of real gate code');
if (!block.includes('ACCESS DENIED') || !block.includes('dsu-bad')) {
  console.log('FAIL: extracted block is not the patched version');
  process.exit(1);
}

const failures = [];
function check(name, ok, detail) {
  console.log((ok ? 'PASS ' : 'FAIL ') + name + (detail === undefined ? '' : '  :: ' + detail));
  if (!ok) failures.push(name);
}

function makeElement(name) {
  const handlers = new Map();
  const classes = new Set();
  return {
    name,
    classes,
    listeners: handlers,
    value: '',
    offsetWidth: 1,
    classList: {
      add: (c) => classes.add(c),
      remove: (c) => classes.delete(c),
      contains: (c) => classes.has(c),
    },
    addEventListener: (type, fn) => handlers.set(type, fn),
    removeEventListener: (type) => handlers.delete(type),
    contains: () => false,
    focus() {},
  };
}

function build(password, skipped) {
  const ui = { btn: makeElement('btn'), action: makeElement('action'), pass: null, hint: { innerHTML: '' } };
  const docHandlers = new Map();
  const document = {
    addEventListener: (type, fn) => docHandlers.set(type, fn),
    removeEventListener: (type) => docHandlers.delete(type),
  };
  const C = { requireInteraction: true, password };
  const waiters = [];
  const factory = new Function(
    'ui',
    'C',
    'skipped',
    'waiters',
    'document',
    'setTimeout',
    block + '\nreturn waitAction;',
  );
  const waitAction = factory(ui, C, skipped, waiters, document, () => 0);
  return { ui, document, docHandlers, waitAction, waiters };
}

const flush = () => new Promise((resolve) => setImmediate(resolve));

function mountPass(ui) {
  const row = makeElement('row');
  const entry = makeElement('input');
  entry.parentNode = row;
  ui.pass = entry;
  return { row, entry };
}

function key(harness, keyName, target) {
  const handler = harness.docHandlers.get('keydown');
  let prevented = false;
  if (handler) handler({ key: keyName, target, preventDefault: () => { prevented = true; } });
  return prevented;
}

/* ---- case 1: no password configured — original behaviour must be intact ---- */
{
  const h = build('', false);
  let resolved = false;
  h.waitAction({ action: 'confirm' }).then(() => { resolved = true; });
  await flush();
  h.ui.btn.listeners.get('click')({ target: h.ui.btn, preventDefault() {} });
  await flush();
  check('no password: button click advances', resolved);

  const h2 = build('', false);
  let r2 = false;
  h2.waitAction({ action: 'confirm' }).then(() => { r2 = true; });
  await flush();
  key(h2, 'Enter', h2.ui.btn);
  await flush();
  check('no password: Enter advances', r2);

  const h3 = build('', false);
  let r3 = false;
  h3.waitAction({ action: 'confirm' }).then(() => { r3 = true; });
  await flush();
  h3.ui.action.listeners.get('click')({ target: h3.ui.action, preventDefault() {} });
  await flush();
  check('no password: click on the action area advances', r3);

  const h4 = build('', true);
  let r4 = false;
  h4.waitAction({ action: 'confirm' }).then(() => { r4 = true; });
  await flush();
  check('no password + skipped: resolves immediately', r4);
}

/* ---- case 2: password configured ---- */
{
  const h = build('hunter2', false);
  let resolved = false;
  h.waitAction({ action: 'confirm' }).then(() => { resolved = true; });
  await flush();
  const { entry } = mountPass(h.ui);

  h.ui.action.listeners.get('click')({ target: h.ui.action, preventDefault() {} });
  await flush();
  check('password: clicking empty space does NOT advance', !resolved);

  key(h, ' ', h.ui.btn);
  await flush();
  check('password: Space outside the field does NOT advance', !resolved);

  entry.value = 'wrong';
  key(h, 'Enter', entry);
  await flush();
  check('password: wrong value does NOT advance', !resolved);
  check('password: wrong value clears the field', entry.value === '');
  check('password: wrong value marks the row', h.ui.pass.parentNode.classList.contains('dsu-bad'));
  check('password: wrong value shows ACCESS DENIED', h.ui.hint.innerHTML.includes('ACCESS DENIED'));

  key(h, ' ', entry);
  await flush();
  check('password: Space inside the field does NOT advance', !resolved);

  entry.value = 'hunter2';
  key(h, 'Enter', entry);
  await flush();
  check('password: correct value advances', resolved);

  const h2 = build('hunter2', false);
  let r2 = false;
  h2.waitAction({ action: 'confirm' }).then(() => { r2 = true; });
  await flush();
  const second = mountPass(h2.ui);
  second.entry.value = 'hunter2';
  h2.ui.btn.listeners.get('click')({ target: h2.ui.btn, preventDefault() {} });
  await flush();
  check('password: submit button with correct value advances', r2);

  const h3 = build('hunter2', true);
  let r3 = false;
  h3.waitAction({ action: 'confirm' }).then(() => { r3 = true; });
  await flush();
  check('password + skipped: still leaves (never locks the screen)', r3);

  const h4 = build('hunter2', false);
  let r4 = false;
  h4.waitAction({ action: 'grant' }).then(() => { r4 = true; });
  await flush();
  mountPass(h4.ui);
  h4.ui.btn.listeners.get('click')({ target: h4.ui.btn, preventDefault() {} });
  await flush();
  check('password: step 1 (grant) is not gated', r4);
}

console.log('failures: ' + failures.length);
process.exit(failures.length ? 1 : 0);
