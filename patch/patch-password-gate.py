"""Add an optional passphrase gate to step 2 (身份资料确认 / IDENTITY VERIFICATION).

Applies exact-string patches to the vendored plugin, asserting every anchor is
found exactly once so a silent no-op is impossible.

  lib/index.js   register `password` in the host DEFAULTS (normalize() only keeps
                 keys that exist there, and the whole config is injected into the
                 page, so this is what carries the value to the browser)
  lib/splash.js  same key in the page-side DEFAULTS; a passphrase row inside the
                 identity card; submission logic that refuses to advance unless
                 the typed value matches
  lib/splash.css styles for the entry row, focus and the rejection shake
"""

import io
import os
import sys

ROOT = r"%WORKSPACE%\plugins\dsh-startup-screen"

INDEX_DEFAULTS_OLD = """  accessLevel: '3',
  brand1: 'DEEPSEEK',"""
INDEX_DEFAULTS_NEW = """  accessLevel: '3',
  /* 第二步「身份资料确认」的访问口令：留空 = 与原来一致（点按钮 / 回车即通过）；
     非空 = 必须输入正确口令才能进入下一步。跳过与超时兜底仍然有效，不会把界面锁死。 */
  password: '',
  brand1: 'DEEPSEEK',"""

SPLASH_DEFAULTS_OLD = """    accessLevel: '3',
    brand1: 'DEEPSEEK',"""
SPLASH_DEFAULTS_NEW = """    accessLevel: '3',
    /* 第二步「身份资料确认」的访问口令（与 Host 侧 DEFAULTS 保持一致） */
    password: '',
    brand1: 'DEEPSEEK',"""

SHOW_OLD = """  function showAction(step) {
    ui.btnZh.textContent = step.btnZh
    ui.btnEn.textContent = step.btnEn
    ui.card.hidden = step.action !== 'confirm'
    if (step.action === 'confirm') {
      ui.card.innerHTML = ''
      /* 纯中文标签 + 数字/名称，去掉英文双写与主机行，别堆信息 */
      var rows = [
        ['身份名称', C.identity, true],
        ['身份编号', C.identityId, false],
        ['权限等级', C.accessLevel, false]
      ]
      rows.forEach(function (r) {
        var row = el('div', 'dsu-card-row')
        row.appendChild(el('span', null, r[0]))
        row.appendChild(el('b', r[2] ? 'dsu-zhname' : null, r[1]))
        ui.card.appendChild(row)
      })
    }
    ui.hint.innerHTML = '按 <kbd>Enter</kbd> / <kbd>Space</kbd>，或点击按钮继续'
    ui.action.classList.add('dsu-in')
    ui.btn.classList.add('dsu-pulse')
  }"""

SHOW_NEW = """  function showAction(step) {
    ui.btnZh.textContent = step.btnZh
    ui.btnEn.textContent = step.btnEn
    ui.card.hidden = step.action !== 'confirm'
    ui.pass = null
    /* 口令闸门：只有「身份资料确认」这一步，且配置里真的设了口令时才出现；
       没设口令时下面每一处都和原版逐字一致。 */
    var gate = step.action === 'confirm' ? String(C.password || '') : ''
    if (step.action === 'confirm') {
      ui.card.innerHTML = ''
      /* 纯中文标签 + 数字/名称，去掉英文双写与主机行，别堆信息 */
      var rows = [
        ['身份名称', C.identity, true],
        ['身份编号', C.identityId, false],
        ['权限等级', C.accessLevel, false]
      ]
      rows.forEach(function (r) {
        var row = el('div', 'dsu-card-row')
        row.appendChild(el('span', null, r[0]))
        row.appendChild(el('b', r[2] ? 'dsu-zhname' : null, r[1]))
        ui.card.appendChild(row)
      })
      if (gate) {
        var wrap = el('div', 'dsu-card-row dsu-pass-row')
        wrap.appendChild(el('span', null, '访问口令'))
        var entry = el('input', 'dsu-pass')
        entry.type = 'password'
        entry.autocomplete = 'off'
        entry.spellcheck = false
        entry.setAttribute('aria-label', '访问口令')
        entry.setAttribute('placeholder', 'PASSPHRASE')
        wrap.appendChild(entry)
        ui.card.appendChild(wrap)
        ui.pass = entry
      }
    }
    ui.hint.innerHTML = gate
      ? '输入访问口令后按 <kbd>Enter</kbd> 确认'
      : '按 <kbd>Enter</kbd> / <kbd>Space</kbd>，或点击按钮继续'
    ui.action.classList.add('dsu-in')
    ui.btn.classList.add('dsu-pulse')
    if (ui.pass) {
      /* 卡片入场动画结束后再聚焦，避免在动画中途抢焦点 */
      setTimeout(function () { try { ui.pass.focus() } catch (err) { /* noop */ } }, 460)
    }
  }"""

WAIT_OLD = """  function waitAction() {
    return new Promise(function (resolve) {
      if (skipped || !C.requireInteraction) return resolve()
      var done = false
      function fin() {
        if (done) return
        done = true
        cleanup()
        resolve()
      }
      function onKey(e) {
        if (e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') { e.preventDefault(); fin() }
      }
      function onClick(e) { e.preventDefault(); fin() }
      function cleanup() {
        ui.btn.removeEventListener('click', onClick)
        ui.action.removeEventListener('click', onClick)
        document.removeEventListener('keydown', onKey)
        var i = waiters.indexOf(fin)
        if (i >= 0) waiters.splice(i, 1)
      }
      ui.btn.addEventListener('click', onClick)
      ui.action.addEventListener('click', onClick)
      document.addEventListener('keydown', onKey)
      waiters.push(fin)
    })
  }"""

WAIT_NEW = """  var HINT_PASS = '输入访问口令后按 <kbd>Enter</kbd> 确认'

  function waitAction(step) {
    return new Promise(function (resolve) {
      if (skipped || !C.requireInteraction) return resolve()
      /* 第二步的口令闸门。need 为空时，这个函数的行为与改动前逐行等价：
         按钮、动作区、Enter、Space 任一都能放行。 */
      var need = step && step.action === 'confirm' ? String(C.password || '') : ''
      var done = false
      function fin() {
        if (done) return
        done = true
        cleanup()
        resolve()
      }
      function reject() {
        if (done || !ui.pass) return
        var entry = ui.pass
        var row = entry.parentNode
        try { entry.value = '' } catch (err) { /* noop */ }
        if (row) {
          row.classList.remove('dsu-bad')
          void row.offsetWidth          /* 强制重排，重复输错也能重放抖动 */
          row.classList.add('dsu-bad')
          setTimeout(function () { row.classList.remove('dsu-bad') }, 900)
        }
        ui.hint.innerHTML = '口令不正确 · ACCESS DENIED — 请重新输入'
        try { entry.focus() } catch (err) { /* noop */ }
        setTimeout(function () { if (!done) ui.hint.innerHTML = HINT_PASS }, 1700)
      }
      function submit() {
        if (!need) return fin()
        if (!ui.pass) return fin()
        if (String(ui.pass.value || '') === need) return fin()
        reject()
      }
      function onKey(e) {
        var inPass = !!ui.pass && e.target === ui.pass
        if (e.key === 'Enter') { e.preventDefault(); submit(); return }
        /* 口令模式下的空格属于口令本身，不能当放行键 */
        if ((e.key === ' ' || e.key === 'Spacebar') && !inPass && !need) { e.preventDefault(); fin() }
      }
      function onClick(e) {
        if (ui.btn && (e.target === ui.btn || ui.btn.contains(e.target))) {
          e.preventDefault()
          submit()
          return
        }
        /* 设了口令就不认「点空白处」这条捷径，否则门禁形同虚设 */
        if (need) return
        e.preventDefault()
        fin()
      }
      function cleanup() {
        ui.btn.removeEventListener('click', onClick)
        ui.action.removeEventListener('click', onClick)
        document.removeEventListener('keydown', onKey)
        var i = waiters.indexOf(fin)
        if (i >= 0) waiters.splice(i, 1)
      }
      ui.btn.addEventListener('click', onClick)
      ui.action.addEventListener('click', onClick)
      document.addEventListener('keydown', onKey)
      waiters.push(fin)
    })
  }"""

HIDE_OLD = """  function hideAction() {
    ui.action.classList.remove('dsu-in')
    ui.btn.classList.remove('dsu-pulse')
  }"""
HIDE_NEW = """  function hideAction() {
    ui.action.classList.remove('dsu-in')
    ui.btn.classList.remove('dsu-pulse')
    ui.pass = null
  }"""

CALL_OLD = """          showAction(step)
          return wait(520).then(function () { return waitAction() }).then(function () {"""
CALL_NEW = """          showAction(step)
          return wait(520).then(function () { return waitAction(step) }).then(function () {"""

CSS_OLD = ".dsu-card-row b.dsu-zhname { font-family: var(--dsu-zh); letter-spacing: 0.1em; }"
CSS_NEW = """.dsu-card-row b.dsu-zhname { font-family: var(--dsu-zh); letter-spacing: 0.1em; }

/* ── 第二步的口令闸门（可选）：配了 password 才出现 ─────────────────────── */
.dsu-pass-row { align-items: center; }
.dsu-pass {
  width: 152px;
  padding: 2px 0 5px;
  border: 0;
  border-bottom: 1px solid var(--dsu-hair);
  background: transparent;
  text-align: right;
  font-family: var(--dsu-mono);
  font-size: 13px;
  letter-spacing: 0.22em;
  color: var(--dsu-ink);
  outline: none;
  transition: border-color 220ms ease;
}
.dsu-pass::placeholder { color: var(--dsu-muted); opacity: 0.45; letter-spacing: 0.14em; }
.dsu-pass:focus { border-bottom-color: var(--dsu-accent, #ff7500); }
.dsu-pass-row.dsu-bad .dsu-pass { border-bottom-color: #ff3b30; }
.dsu-pass-row.dsu-bad { animation: dsu-bad 340ms cubic-bezier(0.36, 0.07, 0.19, 0.97) 2; }
@keyframes dsu-bad {
  0%, 100% { transform: translateX(0); }
  20% { transform: translateX(-5px); }
  40% { transform: translateX(5px); }
  60% { transform: translateX(-3px); }
  80% { transform: translateX(3px); }
}"""

PATCHES = [
    ("lib/index.js", INDEX_DEFAULTS_OLD, INDEX_DEFAULTS_NEW),
    ("lib/splash.js", SPLASH_DEFAULTS_OLD, SPLASH_DEFAULTS_NEW),
    ("lib/splash.js", SHOW_OLD, SHOW_NEW),
    ("lib/splash.js", WAIT_OLD, WAIT_NEW),
    ("lib/splash.js", HIDE_OLD, HIDE_NEW),
    ("lib/splash.js", CALL_OLD, CALL_NEW),
    ("lib/splash.css", CSS_OLD, CSS_NEW),
]

targets = {}
for rel, _old, _new in PATCHES:
    if rel not in targets:
        with io.open(os.path.join(ROOT, *rel.split("/")), encoding="utf-8") as handle:
            targets[rel] = handle.read()

failures = []
for rel, old, new in PATCHES:
    count = targets[rel].count(old)
    if count != 1:
        failures.append("{}: anchor found {} times".format(rel, count))
        continue
    targets[rel] = targets[rel].replace(old, new, 1)
    print("patched  {:<16} {} chars -> {} chars".format(rel, len(old), len(new)))

if failures:
    print("FAILED, nothing written:")
    for item in failures:
        print("  " + item)
    sys.exit(1)

for rel, text in targets.items():
    with io.open(os.path.join(ROOT, *rel.split("/")), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    print("wrote    {:<16} {} bytes".format(rel, len(text.encode("utf-8"))))

print("ok")
