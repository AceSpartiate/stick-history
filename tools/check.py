#!/usr/bin/env python3
"""
Pre-flight checks for index.html.

These exist because the same handful of mistakes kept shipping. Each check below
corresponds to a bug that reached the player at least once. Run after any change:

    python3 tools/check.py        (python tools/check.py on Windows)

Exit code is non-zero if anything fails, so it can gate a commit - which is
what .githooks/pre-commit does with it.

Check 1 needs `node` on PATH; it is the only external dependency and it SKIPS
rather than failing when node is absent, so checks 2-8 still run on a machine
that has only Python.
"""
import re, sys, os, subprocess, tempfile, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC  = os.path.join(ROOT, "index.html")
s    = open(SRC, encoding="utf-8").read()
fail = []
def ok(msg):   print("  ok    " + msg)
def bad(msg):  print("  FAIL  " + msg); fail.append(msg)

print("\n1. JavaScript parses")
blocks = re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', s, re.S)
js = "\n".join(blocks)
# node is the one thing here that is not Python. Without it this used to die on
# a CreateProcess error and take checks 2-8 down with it - so a school machine
# with no Node, or a commit hook running anywhere but this desk, lost every
# check rather than one. Skip loudly instead.
if shutil.which("node") is None:
    print("  skip  node not on PATH — syntax unchecked (install Node.js to enable)")
else:
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(js); tmp = f.name
    r = subprocess.run(["node", "--check", tmp], capture_output=True, text=True)
    os.unlink(tmp)
    ok("syntax") if r.returncode == 0 else bad("syntax:\n" + r.stderr)

print("\n2. Every interactable action is fully wired")
# A new action needs a dispatcher branch AND a prompt verb. Missing either one
# presents to the player as "I press the button and nothing happens".
used    = set(re.findall(r'action:"([a-z]+)"', s))
handled = set(re.findall(r'a==="([a-z]+)"', s))
verbs   = set(re.findall(r'best\.action==="([a-z]+)"', s))
d = sorted(used - handled)
v = sorted(used - verbs)
ok("all %d actions dispatched" % len(used)) if not d else bad("not dispatched: %s" % d)
ok("all actions have a prompt verb")        if not v else bad("no prompt verb: %s" % v)

print("\n3. Every modal is registered")
# Unregistered modals are invisible to anyMod`alOpen and closeAllModals, so
# hotkeys fire underneath them and the pause state desyncs.
m = re.search(r'const MODALS=\[([^\]]+)\]', s)
reg = {x.strip().strip('"') for x in m.group(1).split(",")} if m else set()
decl = set(re.findall(r'class="modal[^"]*" id="([A-Za-z0-9_]+)"', s))
miss = sorted(decl - reg)
ok("all %d modals registered" % len(decl)) if not miss else bad("unregistered: %s" % miss)

print("\n4. Every element the JS reaches for exists")
ids  = set(re.findall(r'\bid="([A-Za-z0-9_]+)"', s))
# built into innerHTML, either escaped or inside single quotes
dyn  = set(re.findall(r'id=\\?["\']([A-Za-z0-9_]+)\\?["\']', s))
refs = set(re.findall(r'\$\("([A-Za-z0-9_]+)"\)', s))
# An id may also be passed as an argument to a builder that writes the markup -
# gGauge("gChargeFill",...) never appears as id="gChargeFill" anywhere. So the
# useful question is not "does it exist" but "is the read GUARDED". An unguarded
# read of a missing element throws; a guarded one degrades quietly.
gone, unguarded = sorted(refs - ids - dyn), []
for nm in gone:
    lines = [ln for ln in s.split("\n") if '$("%s")' % nm in ln]
    if any("if(" not in ln for ln in lines): unguarded.append(nm)
if not gone:
    ok("no dangling element references")
elif not unguarded:
    print("  note  built at runtime, all reads guarded: %s" % gone)
else:
    bad("unguarded reads of missing elements: %s" % unguarded)

print("\n5. onclick handlers bind to real elements")
click = set(re.findall(r'\$\("([A-Za-z0-9_]+)"\)\.onclick', s))
gone2 = sorted(click - ids - dyn)
ok("all handlers bound") if not gone2 else bad("bound to nothing: %s" % gone2)

print("\n6. No call to an undefined function")
# scan the SCRIPT blocks only - the stylesheet is full of rgba(), calc(), var()
t = re.sub(r'/\*.*?\*/', '', js, flags=re.S)
t = re.sub(r'(?<!:)//[^\n]*', '', t)
t = re.sub(r'"(?:[^"\\\n]|\\.)*"', '""', t)
t = re.sub(r"'(?:[^'\\\n]|\\.)*'", "''", t)
dec = set(re.findall(r'\bfunction\s+([A-Za-z_$][\w$]*)', t))
for mm in re.finditer(r'\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)', t): dec.add(mm.group(1))
# multi-declarations on one line: const X=..., Y=...
# multi-declarations: const X=..., Y=...  (comma-splitting breaks on function
# bodies, so match the ", NAME=" shape directly instead)
for mm in re.finditer(r',\s*([A-Za-z_$][\w$]*)\s*=', t): dec.add(mm.group(1))
for mm in re.finditer(r'function\s*[A-Za-z_$\w]*\s*\(([^)]*)\)', t):
    for p in mm.group(1).split(","):
        p = p.strip()
        if re.fullmatch(r'[A-Za-z_$][\w$]*', p): dec.add(p)
for mm in re.finditer(r'catch\s*\(\s*([A-Za-z_$][\w$]*)', t): dec.add(mm.group(1))
for mm in re.finditer(r'for\s*\(\s*(?:const|let)\s+([A-Za-z_$][\w$]*)\s+of', t): dec.add(mm.group(1))
called = {mm.group(1) for mm in re.finditer(r'(?<![.\w$])([A-Za-z_$][\w$]*)\s*\(', t)}
KW   = {'if','for','while','switch','catch','return','function','typeof','new','else',
        'do','try','delete','void','in','of','case','throw'}
HOST = {'Math','JSON','Object','Array','String','Number','Boolean','Date','Promise','Map',
        'Set','WeakSet','WeakMap','parseInt','parseFloat','isNaN','isFinite','setTimeout',
        'setInterval','clearTimeout','clearInterval','requestAnimationFrame','confirm',
        'cancelAnimationFrame','console','document','window','THREE','performance','alert',
        'Float32Array','Uint8Array','Error','RegExp','SpeechSynthesisUtterance','prompt',
        'AudioContext','webkitAudioContext','encodeURIComponent','decodeURIComponent',
        'btoa','atob','escape','unescape','fetch','structuredClone',
        # browser globals, not project functions. This check exists to catch a
        # mistyped function name of OURS; a standard constructor tripping it is the
        # allowlist being short, not a fault in the game.
        'URL','URLSearchParams','sessionStorage','localStorage','Intl','Symbol'}
undef = sorted(called - dec - KW - HOST)
ok("no undefined calls") if not undef else bad("undefined: %s" % undef)

print("\n7. Cutscene steps are long enough for their narration")
# csNext takes MAX(given, 2.6, spoken). Anything much over ~60s is a wall the
# player cannot skip past quickly; measure and tighten the writing, not the timer.
long = []
for mm in re.finditer(r'narrate:"((?:[^"\\]|\\.)*)"', s):
    words = len(re.sub(r'\\u[0-9a-fA-F]{4}', ' ', mm.group(1)).split())
    secs  = words / 2.3 + 0.8
    if secs > 20: long.append((round(secs, 1), mm.group(1)[:52]))
if long:
    print("  note  %d narration lines exceed 20s when spoken:" % len(long))
    for secs, txt in sorted(long, reverse=True)[:5]:
        print("        %5.1fs  %s..." % (secs, txt))
    print("        (not a failure - but a scene is only as short as its writing)")
else:
    ok("no narration line runs past 20s")

print("\n8. No texture or image assets")
# The project is deliberately procedural. An <img>, a TextureLoader, or a url()
# in CSS means the single-file, no-assets property has been broken.
tex = []
if re.search(r'TextureLoader|\.load\(\s*["\']', s): tex.append("TextureLoader")
if re.search(r'<img\b', s): tex.append("<img>")
if re.search(r'url\(\s*["\']?(?!data:)', s): tex.append("css url()")
ok("still texture-free") if not tex else bad("assets introduced: %s" % tex)

print("\n" + ("PASS" if not fail else "FAILED %d check(s)" % len(fail)))
sys.exit(0 if not fail else 1)
