/**
 * Verify the config plumbing with the real host code.
 *
 * Extracts DEFAULTS + the key tables + normalize() out of lib/index.js and runs
 * them against the actual config file, proving that:
 *   - the file parses as the host parses it (readFileSync utf8 + JSON.parse),
 *   - `password` survives normalize() and therefore reaches window.__DSH_STARTUP__,
 *   - an unregistered key is dropped, which is why it had to be added to DEFAULTS.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const PLUGIN = String.raw`%WORKSPACE%\plugins\dsh-startup-screen\lib\index.js`;
const CONFIG = join(process.env.USERPROFILE, '.dsh', 'dsh-startup.json');

const source = readFileSync(PLUGIN, 'utf8');
const lines = source.split('\n');

function block(startPattern) {
  const start = lines.findIndex((line) => line.startsWith(startPattern));
  if (start < 0) throw new Error('anchor not found: ' + startPattern);
  // a declaration that already closes on its own line (e.g. the one-line key
  // arrays) must not swallow the blocks that follow it
  if (!/[\[{]\s*$/.test(lines[start])) return lines[start];
  for (let i = start + 1; i < lines.length; i += 1) {
    if (lines[i] === '}' || lines[i] === ']') return lines.slice(start, i + 1).join('\n');
  }
  throw new Error('unterminated block: ' + startPattern);
}

const parts = [
  block('const DEFAULTS = {'),
  block('const TEXT_KEYS = ['),
  block('const COLOR_KEYS = ['),
  block('const ENUMS = {'),
  block('const BOOL_KEYS = ['),
  block('const RANGES = {'),
];

const normalizeStart = lines.findIndex((line) => line.startsWith('function normalize(input) {'));
if (normalizeStart < 0) throw new Error('normalize not found');
let normalizeEnd = -1;
for (let i = normalizeStart + 1; i < lines.length; i += 1) {
  if (lines[i] === '}') { normalizeEnd = i; break; }
}
parts.push(lines.slice(normalizeStart, normalizeEnd + 1).join('\n'));

const build = new Function(parts.join('\n\n') + '\nreturn { DEFAULTS, normalize };');
const { DEFAULTS, normalize } = build();

const failures = [];
const check = (name, ok, detail) => {
  console.log((ok ? 'PASS ' : 'FAIL ') + name + (detail === undefined ? '' : '  :: ' + detail));
  if (!ok) failures.push(name);
};

check('host DEFAULTS registers password', Object.prototype.hasOwnProperty.call(DEFAULTS, 'password'), JSON.stringify(DEFAULTS.password));

const raw = readFileSync(CONFIG, 'utf8');
check('config has no BOM', raw.charCodeAt(0) !== 0xfeff);
const fileConfig = JSON.parse(raw);
check('config parses', typeof fileConfig === 'object');
check('file holds the passphrase as a string', typeof fileConfig.password === 'string', String(fileConfig.password).length + ' chars');

const resolved = normalize(fileConfig);
check('normalize keeps the passphrase', resolved.password === fileConfig.password, JSON.stringify(resolved.password));
check(
  'value survives as a string, leading zero intact',
  typeof resolved.password === 'string' &&
    resolved.password === fileConfig.password &&
    (fileConfig.password[0] !== '0' || resolved.password[0] === '0'),
  JSON.stringify(resolved.password),
);
check('other settings fall back to defaults', resolved.identity === DEFAULTS.identity && resolved.mode === DEFAULTS.mode, resolved.identity + ' / ' + resolved.mode);

const dropped = normalize({ ...fileConfig, definitelyUnknownKey: 'x' });
check('unregistered keys are dropped (why DEFAULTS matters)', dropped.definitelyUnknownKey === undefined);

const injected = JSON.stringify(resolved);
check('the injected config carries it', injected.includes(JSON.stringify(fileConfig.password)));

console.log('failures: ' + failures.length);
process.exit(failures.length ? 1 : 0);
