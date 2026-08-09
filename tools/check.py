#!/usr/bin/env python3
"""
Pre-flight checks for index.html.

These exist because the same handful of mistakes kept shipping. Each check below
corresponds to a bug that reached the player at least once. Run after any change:

    python3 tools/check.py        (python tools/check.py on Windows)

Exit code is non-zero if anything fails, so it can gate a commit - which is
what .githooks/pre-commit does with it.

Check 1 needs `node` on PATH, and check 10 asks `git` what is staged. Those are the
only external dependencies, and both SKIP rather than fail when the tool is absent,
so every other check still runs on a machine that has only Python.
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
# Comma-separated declarations with NO initialiser - `let renderer,scene,cam;` -
# were invisible to the pattern above, which requires an `=`. Walk each
# declaration list and take the leading identifier of every top-level comma part,
# tracking bracket depth so a call or object inside an initialiser is not mistaken
# for another declared name.
for mm in re.finditer(r'\b(?:const|let|var)\s+([^;{}\n]*)', t):
    depth, buf, parts = 0, "", []
    for ch in mm.group(1):
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(buf); buf = ""
        else:
            buf += ch
    parts.append(buf)
    for p in parts:
        m2 = re.match(r'\s*([A-Za-z_$][\w$]*)', p)
        if m2: dec.add(m2.group(1))
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

print("\n6b. No assignment to an undeclared variable")
# The bug this exists for: `camKick` was written in six places and declared in
# none. The file is strict mode, so every write threw a ReferenceError - and the
# one in discharge() sits three lines in, so the whole firing path after it never
# ran. The piece had never actually fired a ball, and check 6 could not see it
# because that check looks for CALLS to undefined functions, not writes to
# undeclared names.
#
# Only bare `name = ...` at a statement boundary counts. `a.b = ...`, `a[i] = ...`,
# `==`, `===`, `!=`, `>=`, `<=`, `+=` and friends are all excluded, as are the
# declaration keywords themselves.
assigned = {}
for mm in re.finditer(r'(?:^|[;{}\)]|\belse\b)\s*([A-Za-z_$][\w$]*)\s*=(?![=>])', t):
    nm = mm.group(1)
    if nm in KW or nm in HOST:
        continue
    assigned.setdefault(nm, t[:mm.start()].count("\n") + 1)
wild = sorted(n for n in assigned if n not in dec)
if not wild:
    ok("every assignment targets a declared name")
else:
    bad("assigned but never declared (strict mode throws): %s"
        % ", ".join("%s (~line %d of the script blocks)" % (n, assigned[n]) for n in wild))

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

print("\n9. No `typeof X` guard on a const/let declared later")
# `typeof` only swallows GENUINELY UNDECLARED names. On a let/const that has not
# been reached yet - the temporal dead zone - it throws like any other read. So
# `if(typeof CHAPTERS==="undefined")return false;` written above the declaration
# is not a guard, it is a fatal error - and because the page still renders it is
# nearly invisible: every statement after it is skipped, so every handler bound
# below the failure point is silently null. Cost a real debugging round.
# Use `try{ x=CHAPTERS; }catch(e){ ... }` instead.
decl = {}
for mm in re.finditer(r'^\s*(?:const|let)\s+([A-Za-z_$][\w$]*)\s*=', js, re.M):
    decl.setdefault(mm.group(1), mm.start())
tdz = set()
for mm in re.finditer(r'typeof\s+([A-Za-z_$][\w$]*)', js):
    n = mm.group(1)
    if n in decl and mm.start() < decl[n]:
        tdz.add((n, js.count("\n", 0, mm.start()) + 1))
# Whether each of these is FATAL depends on when the surrounding code RUNS, which
# this tool cannot know: inside a function called long after load, `typeof X` is
# fine. So this is a note, not a failure - and the reliable detector is the
# runtime probe in CLAUDE.md, which asks the loaded page whether the script
# actually reached its own last line.
if tdz:
    print("  note  %d `typeof` reads of a const/let declared later in the file." % len(tdz))
    print("        Safe only if that code runs AFTER the declaration is reached.")
    print("        Fatal at load time - and the page still renders, so it hides.")
    for n, ln in sorted(tdz)[:8]:
        print("          %-16s ~script line %d" % (n, ln))
else:
    ok("no typeof-before-declaration guards")

print("\n10. The build stamp agrees with itself")
# tools/stamp.py writes ONE id to two places, and they only mean anything as a pair:
# the page compares the BUILD baked into it against the version.txt it fetches, and
# reads any difference as "I am stale". So a mismatch is not a quiet mismatch. The
# page reloads once, still disagrees, and then parks the player behind "An update is
# ready, and your browser is serving an older copy" with a button that cannot help,
# for the rest of the session - the exact confusion the stamp exists to prevent,
# wearing the stamp's own uniform. Nothing caught this before; the script writing
# both values was the only thing holding them together.
VER = os.path.join(ROOT, "version.txt")


def stamp_pair(html, ver):
    """The BUILD baked into some index.html, and the id in some version.txt."""
    m = re.search(r'const BUILD="([^"]*)"', html)
    return (m.group(1) if m else None), ver.strip()


def staged(path):
    """A file's STAGED content, or None if git or the index cannot supply it."""
    if shutil.which("git") is None:
        return None
    r = subprocess.run(["git", "show", ":" + path], capture_output=True, cwd=ROOT)
    # Decoded here rather than with text=True: index.html is UTF-8, and on Windows
    # text=True decodes as cp1252, which raises on bytes that are perfectly ordinary
    # inside a UTF-8 sequence. A check must not be the thing that crashes.
    return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else None


if not os.path.exists(VER):
    bad("version.txt is missing - the page's update check has nothing to fetch")
else:
    wb, wv = stamp_pair(s, open(VER, encoding="utf-8").read())
    if wb is None:
        bad('no `const BUILD="..."` in index.html - tools/stamp.py cannot write it either')
    elif wb != wv:
        bad("index.html says %r and version.txt says %r\n"
            "        run `python tools/stamp.py`, which writes both at once" % (wb, wv))
    else:
        ok("index.html and version.txt both say %s" % wb)

# The nine checks above read the working tree, and for this one that is not enough:
# the likeliest way to ship a split pair is to stage one file without the other, and
# the working tree looks perfect in precisely that case. So the index gets asked too.
# No git, or files not yet tracked, is a skip rather than a failure - the same bargain
# check 1 makes with node. A path-limited `git commit -- one-file` can still slip past
# this, because the hook is shown the whole index either way.
sh, sv = staged("index.html"), staged("version.txt")
if sh is None or sv is None:
    print("  skip  staged pair unchecked (no git, or the files are not in the index)")
else:
    gb, gv = stamp_pair(sh, sv)
    if gb != gv:
        bad("the STAGED copies disagree: index.html says %r, version.txt says %r\n"
            "        stage them together - `git add index.html version.txt`" % (gb, gv))
    else:
        ok("the staged pair agrees too")

print("\n11. Persisted state agrees with the save whitelist")
# `saveBlob()` lists every persisted key BY HAND and `applyBlob()` reads them back
# BY HAND. So a new key on S is dropped silently unless it is added in both places -
# and the failure only shows when a player resumes, which no test does. This is the
# class of bug that costs a chapter's outcome and looks like nothing at all.
#
# Two directions, because both are real:
#   written but not saved   - the outcome vanishes on resume
#   saved but not applied   - it is written to storage and never read back, which is
#                             worse, because the save LOOKS complete
#
# Anything genuinely per-session goes on TRANSIENT below, with a reason. That list is
# the whole point: it forces the question to be answered once, in writing, instead of
# being answered by accident every time somebody adds a field.

def body_of(src, name):
    """the balanced-brace body of `function name(){...}`, or None"""
    i = src.find("function " + name + "(")
    if i < 0: return None
    j = src.find("{", i)
    if j < 0: return None
    d = 0
    for k in range(j, len(src)):
        c = src[k]
        if c == "{": d += 1
        elif c == "}":
            d -= 1
            if d == 0: return src[j:k + 1]
    return None

# per-session only, never persisted - each one needs a reason to be on this list
#
# THIS LIST STARTED WITH FIVE GUESSES ON IT AND THREE WERE WRONG, WHICH IS THE
# argument for the check existing. Two of them were silencing real bugs: S.spoke is
# documented in the file as "the high-water mark: once a man has been asked out he
# stays asked out" - the exact opposite of re-derivable - and S.councilWarned is read
# back at the muster. Two more named keys that do not exist at all. So: nothing goes
# on this list that has not been READ IN THE FILE, and the reason quotes the code.
TRANSIENT = {}

blob = body_of(s, "saveBlob")
appl = body_of(s, "applyBlob")
if blob is None or appl is None:
    bad("saveBlob() or applyBlob() not found - the save format cannot be checked")
else:
    saved   = set(re.findall(r"\bS\.([A-Za-z_$][\w$]*)", blob))
    applied = set(re.findall(r"\bS\.([A-Za-z_$][\w$]*)\s*=", appl))
    # every place the game WRITES state: S.x = / S.x[...] = / S.x.y = / S.x.push(
    written = set()
    for m in re.finditer(r"\bS\.([A-Za-z_$][\w$]*)\s*(?:=[^=]|\[|\.\w+\s*=[^=]|\.(?:push|pop|shift|unshift|splice|add|delete|set)\s*\()", s):
        written.add(m.group(1))
    # assignments inside applyBlob are the RESTORE, not gameplay state creation
    written -= applied

    lost = sorted(w for w in written if w not in saved and w not in TRANSIENT)
    deaf = sorted(k for k in saved if k not in applied)

    if lost:
        bad("%d state key(s) are written but NOT in saveBlob - they vanish on resume:\n"
            "        %s\n"
            "        add each to saveBlob() AND applyBlob(), or to TRANSIENT in this check with a reason"
            % (len(lost), ", ".join("S." + k for k in lost)))
    else:
        ok("every written state key is persisted (%d keys, %d declared transient)"
           % (len(saved), len(TRANSIENT)))

    if deaf:
        bad("%d key(s) are SAVED but never restored by applyBlob - written to storage and "
            "never read back:\n        %s" % (len(deaf), ", ".join("S." + k for k in deaf)))
    else:
        ok("every saved key is read back by applyBlob")

    # And the version must not be bumped casually: a mismatch discards the save.
    mv = re.search(r"const SAVE_VERSION\s*=\s*(\d+)", s)
    if mv:
        ok("SAVE_VERSION is %s - extending the whitelist needs no bump, applyBlob defaults "
           "every missing key" % mv.group(1))

print("\n12. A consequence is banked the moment it is earned")
# Reported from play: fire a cannon by accident, refresh the page, and it never happened.
# Checkpoints are at boundaries BY DESIGN, so anything earned between two of them lived
# only in memory. The rule now is an asymmetry - progress waits for a boundary, a
# consequence does not - and this is what stops the rule from quietly rotting.
#
# Every write to a key that records something AGAINST the player must be followed closely
# by incur() or saveGame(). Closely, because these are one-or-two-line mutations; a save
# five lines later is usually a different branch.

AGAINST = r"firedGun|shotAMan|killedAMan|corrections|incidents|talkErr|ambushFired|ambushShots|pending"
# where the save format itself is written, and where a run is deliberately wiped
# newRun AND resetRun both exist and both deliberately wipe the record
EXEMPT_FN = ("saveBlob", "applyBlob", "newRun", "resetRun", "musterCode",
             "readMuster", "applyMuster")

lines = s.split("\n")
def fn_at(i):
    """the nearest preceding top-level function name"""
    for j in range(i, -1, -1):
        m = re.match(r"function\s+([A-Za-z_$][\w$]*)", lines[j])
        if m:
            return m.group(1)
    return "?"

unbanked = []
for i, ln in enumerate(lines):
    if not re.search(r"\bS\.(%s)\s*(=[^=]|\+\+|\+=|\.push\()" % AGAINST, ln):
        continue
    if fn_at(i) in EXEMPT_FN:
        continue
    # `if(!S.incidents)S.incidents=[]` is a lazy initialiser, not a consequence. It
    # records nothing against anybody and forcing a save on it would be noise.
    if re.search(r"if\s*\(\s*!\s*S\.\w+\s*\)\s*S\.\w+\s*=\s*(\[\]|\{\})", ln):
        continue
    window = "\n".join(lines[i:i + 4])
    if re.search(r"\bincur\(|\bsaveGame\(|\bcheckpoint\(", window):
        continue
    unbanked.append("line %d in %s(): %s" % (i + 1, fn_at(i), ln.strip()[:78]))

if unbanked:
    bad("%d consequence write(s) are not banked - a refresh erases them:\n        %s\n"
        "        follow each with incur(\"why\"), or add the function to EXEMPT_FN here"
        % (len(unbanked), "\n        ".join(unbanked)))
else:
    ok("every write against the player is followed by incur/saveGame")

# and the unserved-punishment half, which is the part that is easy to drop
if re.search(r"S\.pending\s*=\s*\{", s) and "function resumePenalty" in s \
   and re.search(r"resumePenalty\(\)", s.split("function resumePenalty")[0] +
                 s.split("function resumePenalty")[1]):
    ok("an unserved punishment is recorded and resumed")
else:
    bad("S.pending is set but never resumed - a refresh mid-punishment serves none of it")

print("\n13. The globe agrees with the gazetteer")
# ---- A METHODOLOGY FOR "MAKE THE MAP MORE ACCURATE" ----
# The globe's land is a union of circles. Nudging one to fix a coast silently floods a sea
# somewhere else, and that happened three times in one session: an Anatolia blob closed the
# Black Sea, a pre-existing one closed the Gulf of Mexico, and the Sahara closed the
# Mediterranean. Each was found by accident, one at a time, by a human squinting.
#
# So accuracy stops being taste and becomes a SCORE WITH NAMED FAILURES. A gazetteer of
# places whose answer is not in dispute - cities that must be on land, seas and straits that
# must be water - is run against the same great-circle test the game uses. Every edit to
# GLOBE_LAND is then checked against all of them at once, and a fix that breaks something
# elsewhere cannot ship quietly.
#
# The water list is the half that matters. Land points alone are satisfied by covering the
# planet in land, which is precisely the failure mode of "add blobs until it looks right".
#
# TO IMPROVE THE MAP: add entries here first, watch them fail, then edit GLOBE_LAND until
# they pass. That is the loop, and it converges - because the gazetteer only ever grows.

LAND = [
    ("London",51.5,-0.1),("Plymouth",50.4,-4.1),("Dublin",53.3,-6.3),("Paris",48.9,2.3),
    ("Madrid",40.4,-3.7),("Lisbon",38.7,-9.1),("Rome",41.9,12.5),("Athens",38.0,23.7),
    ("Constantinople",41.0,29.0),("Moscow",55.8,37.6),("Stockholm",59.3,18.1),
    ("Cairo",30.0,31.2),("Timbuktu",16.8,-3.0),("Benin City",6.3,5.6),
    ("Mbanza Kongo",-6.3,14.2),("Cape Town",-33.9,18.4),("Addis Ababa",9.0,38.7),
    ("Isfahan",32.7,51.7),("Agra",27.2,78.0),("Goa",15.5,73.8),("Malacca",2.2,102.2),
    ("Beijing",39.9,116.4),("Kyoto",35.0,135.8),("Manila",14.6,121.0),
    ("Jamestown",37.2,-76.8),("Roanoke",35.9,-75.7),("Mexico City",19.4,-99.1),
    ("Havana",23.1,-82.4),("Cartagena",10.4,-75.5),("Santo Domingo",18.5,-69.9),
    ("Cusco",-13.5,-72.0),("Potosi",-19.6,-65.8),("Rio",-22.9,-43.2),
    ("Sydney",-33.9,151.2),("Perth",-31.9,115.9),("Wellington",-41.3,174.8),
    ("Greenland",72.0,-40.0),("South Pole",-89.0,0.0),
]
WATER = [
    ("mid-Atlantic",30,-40),("mid-Pacific",0,-140),("Indian Ocean",-20,80),
    ("Southern Ocean",-58,20),("Arctic Ocean",85,0),
    ("English Channel",50.0,-1.0),("Irish Sea",53.6,-5.2),("North Sea",56,3),
    ("Baltic",58,19),("Mediterranean",35,18),("Black Sea",43,34),("Red Sea",20,38),
    ("Persian Gulf",27,51),("Bay of Bengal",15,88),("South China Sea",15,114),
    ("Sea of Japan",40,135),("Caribbean",15,-75),("Gulf of Mexico",25,-90),
    ("Hudson Bay",60,-86),("Baffin Bay",73,-65),("Drake Passage",-58,-65),
    ("Tasman Sea",-40,160),("Bass Strait",-40,146),("Mozambique Channel",-18,41),
    ("Gulf of Guinea",0,0),("Sargasso",28,-60),("North Pacific",40,-160),
]

import math
def _blobs(src):
    i = src.find("const GLOBE_LAND=[")
    if i < 0: return None
    j, d = src.find("[", i), 0
    for k in range(j, len(src)):
        if src[k] == "[": d += 1
        elif src[k] == "]":
            d -= 1
            if d == 0: break
    body = src[j:k+1]
    return [(float(a), float(b), float(r)) for a, b, r, _t in
            re.findall(r'\[(-?[\d.]+),(-?[\d.]+),(-?[\d.]+),"(\w)"\]', body)]

def _land(bl, lat, lon):
    for (bla, blo, br) in bl:
        dl = abs(lon - blo)
        if dl > 180: dl = 360 - dl
        cosd = (math.sin(math.radians(lat))*math.sin(math.radians(bla)) +
                math.cos(math.radians(lat))*math.cos(math.radians(bla))*math.cos(math.radians(dl)))
        if math.degrees(math.acos(max(-1.0, min(1.0, cosd)))) <= br: return True
    return False

_bl = _blobs(s)
if _bl is None:
    bad("GLOBE_LAND not found - the globe cannot be checked")
else:
    dry = [n for (n, la, lo) in LAND  if not _land(_bl, la, lo)]
    wet = [n for (n, la, lo) in WATER if     _land(_bl, la, lo)]
    tot = len(LAND) + len(WATER)
    okc = tot - len(dry) - len(wet)
    if dry:
        bad("%d gazetteer LAND point(s) fall in the sea: %s" % (len(dry), ", ".join(dry)))
    if wet:
        bad("%d gazetteer WATER point(s) are covered by land: %s" % (len(wet), ", ".join(wet)))
    if not dry and not wet:
        ok("all %d gazetteer points agree (%d land, %d water) from %d blobs"
           % (tot, len(LAND), len(WATER), len(_bl)))
    # area-weighted land fraction, reported always - the Earth is 29.2%
    land_w = tot_w = 0.0
    for la in range(-88, 89, 2):
        w = math.cos(math.radians(la))
        for lo in range(-179, 180, 2):
            tot_w += w
            if _land(_bl, la, lo): land_w += w
    print("  note  land covers %.1f%% of the sphere (the Earth is 29.2%%), score %d/%d"
          % (100*land_w/tot_w, okc, tot))

print("\n" + ("PASS" if not fail else "FAILED %d check(s)" % len(fail)))
sys.exit(0 if not fail else 1)
