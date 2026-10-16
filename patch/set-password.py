"""Set the step-2 passphrase in the startup-screen config.

Writes UTF-8 *without* a BOM on purpose: the plugin parses this file with
JSON.parse(fs.readFileSync(..., 'utf8')), and a BOM makes that throw — the
throw is swallowed by its try/catch, so a BOM'd file silently falls back to
defaults and the gate would never appear.

The password is written as a JSON string so a leading zero survives.
"""

import io
import json
import os
import sys

PASSWORD = "<PASSPHRASE>"
CONFIG = os.path.join(os.path.expanduser("~"), ".dsh", "dsh-startup.json")

payload = {"password": PASSWORD}
text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

os.makedirs(os.path.dirname(CONFIG), exist_ok=True)
with io.open(CONFIG, "w", encoding="utf-8", newline="\n") as handle:
    handle.write(text)

with open(CONFIG, "rb") as handle:
    raw = handle.read()

problems = []
if raw.startswith(b"\xef\xbb\xbf"):
    problems.append("file starts with a UTF-8 BOM")
try:
    parsed = json.loads(raw.decode("utf-8"))
except Exception as error:  # noqa: BLE001
    problems.append("re-parse failed: {}".format(error))
    parsed = {}
if parsed.get("password") != PASSWORD:
    problems.append("password did not round-trip")
if not isinstance(parsed.get("password"), str):
    problems.append("password is not a JSON string")

print("file     : " + CONFIG)
print("bytes    : {}  bom={}".format(len(raw), raw.startswith(b"\xef\xbb\xbf")))
print("keys     : " + ", ".join(sorted(parsed)))
print("password : {} chars, starts with '{}'".format(len(str(parsed.get("password", ""))), str(parsed.get("password", "?"))[0]))
print("matches  : {}".format(parsed.get("password") == PASSWORD))
print("problems : {}".format(problems if problems else "none"))
sys.exit(1 if problems else 0)
