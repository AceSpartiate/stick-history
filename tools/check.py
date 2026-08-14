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
def nth_newline(txt, n):
    """Index of the nth newline in txt, or len(txt) if there are fewer."""
    i = -1
    for _ in range(n):
        j = txt.find("\n", i + 1)
        if j < 0: return len(txt)
        i = j
    return i
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
# THIS CHECK USED TO MEASURE THE WRONG THING. Its name says "long enough for their
# narration" and it only ever asserted that no single line runs past twenty seconds -
# which is a note about the WRITING, not about whether the shot holding a line lasts
# long enough to finish saying it. It passed green while five of the six shots in the
# opening cut their own line, by up to 5.2 seconds.
#
# Both cutscene systems now derive their duration as max(authored, spoken) at runtime,
# so a short authored time no longer truncates anything. What it DOES mean is that the
# camera finishes its move and then sits still for the remainder - so the gap is worth
# reporting as a note: it tells the author which shots to lengthen so the picture moves
# for as long as the voice is talking.
def _secs(txt):
    return len(re.sub(r'\\u[0-9a-fA-F]{4}', ' ', txt).split()) / 2.3 + 0.8

def _steps(src, key):
    """Every {...} object literal in src that carries `key`, with its authored seconds."""
    out = []
    for mm in re.finditer(key + r':\s*"((?:[^"\\]|\\.)*)"', src):
        # walk back to the { that opens this object, then forward to its }
        i = src.rfind("{", 0, mm.start())
        depth, j = 0, i
        while j < len(src):
            c = src[j]
            if c in "[{(":
                depth += 1
            elif c in "]})":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        step = src[i:j + 1]
        t = re.search(r'\bt:\s*([0-9.]+)', step)
        w = re.search(r'\bwait:\s*([0-9.]+)', step)
        authored = max(float(t.group(1)) if t else 0.0,
                       float(w.group(1)) if w else 0.0)
        out.append((authored, mm.group(1), src.count("\n", 0, i) + 1))
    return out

rows = _steps(s, "narrate") + _steps(s, "say")
long  = [(round(_secs(x[1]), 1), x[1][:52]) for x in rows if _secs(x[1]) > 20]
short = [(round(_secs(a[1]) - max(a[0], 2.6), 1), a[2], a[1][:46])
         for a in rows if _secs(a[1]) - max(a[0], 2.6) > 1.0]

if long:
    bad("%d narration lines exceed 20s when spoken - too long to sit through:\n"
        % len(long)
        + "\n".join("        %5.1fs  %s..." % r for r in sorted(long, reverse=True)[:5]))
else:
    ok("no narration line runs past 20s (%d narrating steps)" % len(rows))

if short:
    print("  note  %d shots are shorter than their own line, so the camera arrives" % len(short))
    print("        and then waits. Not a truncation - both systems hold for the voice -")
    print("        but the picture stops moving while the words carry on:")
    for gap, line, txt in sorted(short, reverse=True)[:6]:
        print("        %5.1fs short  ~line %-6d %s..." % (gap, line, txt))
else:
    ok("every shot lasts as long as the line spoken over it")

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
# restartChapter joins them: being executed wipes the chapter's progress on purpose, and
# it calls saveGame() itself at the end of the wipe.
EXEMPT_FN = ("saveBlob", "applyBlob", "newRun", "resetRun", "musterCode",
             "readMuster", "applyMuster", "restartChapter")

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

print("\n14. Every conversation beat can be finished on its own")
# The chapter's dialogue pool went from 34 choices to 89, most of them ALTERNATIVE wise
# routes - several ways of asking that reach the same insight, so a pupil who cannot see
# one framing can find another. Two things have to stay true of that pool, and neither is
# obvious by eye once a beat carries nine choices:
#
#   A BEAT MUST HAVE AN UNGATED WAY OUT. A wise choice may require an insight earned from
#   another character (needs:) or evidence from a survey (evid:). If EVERY wise choice on
#   a beat were gated, the conversation would stop dead for a player who had not been
#   somewhere else first, with no way forward and nothing saying so.
#
#   AN ALTERNATIVE ROUTE MUST REACH THE SAME ROOM. Every wise choice carries the insight
#   it grants. Two routes on one beat granting DIFFERENT insights is not an alternative
#   door, it is a second lesson hidden behind a coin toss - the player takes one and never
#   learns the other, and the scrivener may ask about either.
import json as _json

def _beats_of(src):
    """(npc id, beat index, [choice source]) for every beat in every npcs:[] block"""
    def _skip(t, j):
        if t.startswith("/*", j):
            e = t.find("*/", j + 2); return len(t) if e < 0 else e + 2
        if t.startswith("//", j):
            e = t.find("\n", j + 2); return len(t) if e < 0 else e + 1
        return j
    def _match(t, i):
        depth, j, instr = 0, i, None
        while j < len(t):
            if not instr:
                k = _skip(t, j)
                if k != j:
                    j = k; continue
            c = t[j]
            if instr:
                if c == "\\": j += 2; continue
                if c == instr: instr = None
            elif c in "\"'": instr = c
            elif c in "[{(": depth += 1
            elif c in "]})":
                depth -= 1
                if depth == 0: return j
            j += 1
        return len(t) - 1
    def _objs(t):
        out, depth, start, instr, j = [], 0, None, None, 0
        while j < len(t):
            if not instr:
                k = _skip(t, j)
                if k != j:
                    j = k; continue
            c = t[j]
            if instr:
                if c == "\\": j += 2; continue
                if c == instr: instr = None
            elif c in "\"'": instr = c
            elif c == "{":
                if depth == 0: start = j
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0 and start is not None:
                    out.append(t[start:j + 1]); start = None
            j += 1
        return out
    rows = []
    for mm in re.finditer(r"\bnpcs:\s*\[", src):
        i = src.index("[", mm.start())
        for npc in _objs(src[i + 1:_match(src, i)]):
            idm = re.search(r'\bid:"([^"]+)"', npc)
            bm = re.search(r"\bbeats:\s*\[", npc)
            if not (idm and bm):
                continue
            bi = npc.index("[", bm.end() - 1)
            for k, beat in enumerate(_objs(npc[bi + 1:_match(npc, bi)])):
                cm = re.search(r"\bchoices:\s*\[", beat)
                if not cm:
                    continue
                ci = beat.index("[", cm.end() - 1)
                rows.append((idm.group(1), k, _objs(beat[ci + 1:_match(beat, ci)])))
    return rows

stuck, split = [], []
nbeats = nchoices = 0
for who, bi, chs in _beats_of(s):
    nbeats += 1
    nchoices += len(chs)
    wise = [c for c in chs if re.search(r"\bwise:true", c)]
    free = [c for c in wise if not re.search(r'\bneeds:"|\bevid:"', c)]
    if wise and not free:
        stuck.append("%s beat %d" % (who, bi))
    titles = set()
    for c in free:
        t = re.search(r'\binsight:\{g:"[a-z]+",b:"((?:[^"\\]|\\.)*)"', c)
        if t:
            titles.add(t.group(1))
    if len(titles) > 1:
        split.append("%s beat %d grants %s by different routes" % (who, bi, sorted(titles)))

if stuck:
    bad("a beat with no ungated way out - the conversation stops dead: %s" % stuck)
else:
    ok("all %d beats have an ungated wise route (%d choices in the pool)" % (nbeats, nchoices))
if split:
    bad("alternative routes on one beat grant DIFFERENT insights:\n        "
        + "\n        ".join(split))
else:
    ok("every route out of a beat reaches the same insight")

print("\n15. No button wired to nothing")
# THE INVERSE OF CHECK 5, AND IT IS THE ONE THAT BIT. Check 5 asks whether every
# $("x").onclick binds to an element that exists. It cannot see a BUTTON THAT NOTHING
# BINDS TO - and that is what shipped: the Errands panel's Close button carried
# data-close="mGoals", an attribute invented on the spot, which appears exactly once in
# the file and which nothing anywhere reads. The button was inert, and the only way out of
# the panel was the Escape key. A dead button is worse than a missing one: it is a door
# with a handle that does not turn.
#
# TWO SIGNALS, both precise enough to be worth failing on:
#   a declared id with no handler anywhere, and
#   a data- attribute used ONCE in the whole file, which means it is a convention that
#   exists only at the place it is written and is read by nobody.
# A BUTTON DOES NOT HAVE TO BE WIRED WITH $("x").onclick TO BE WIRED. Three in this file
# are handled by helpers that take the id or the element - holdTurn("camL",-1),
# gHold($("gPour"),...), const nb=$("endNext") - and an earlier draft of this check called
# all three dead. The honest question is not HOW it is wired but whether the id is
# mentioned in the script at all: a button nothing ever names cannot be wired by anything.
handled = set(re.findall(r'["\'"]([A-Za-z0-9_]+)["\'"]', js))
dead, n = [], 0
for b in re.finditer(r'<button\b[^>]*>', s):
    tag = b.group(0)
    n += 1
    idm = re.search(r'\bid="([A-Za-z0-9_]+)"', tag)
    if idm and idm.group(1) not in handled:
        dead.append('#%s - declared, and nothing binds a handler to it' % idm.group(1))
    for am in re.finditer(r'\b(data-[a-z-]+)=', tag):
        attr = am.group(1)
        # AND IT MAY BE READ IN ITS OTHER NAME. data-site is read as b.dataset.site, so
        # counting the hyphenated form alone called a live attribute dead - which is the
        # same shape of mistake as the bug this check exists for, made by the check.
        parts = attr[5:].split("-")
        camel = parts[0] + "".join(p.capitalize() for p in parts[1:])
        reads = (len(re.findall(re.escape(attr), s)) - 1
                 + len(re.findall(r'dataset\.' + re.escape(camel) + r'\b', s))
                 + len(re.findall(r'getAttribute\(\s*["\']' + re.escape(attr), s)))
        if reads < 1:
            dead.append('%s on a <button> - written once and read nowhere, in either '
                        'its hyphenated or its dataset form' % attr)
if dead:
    bad("%d button(s) wired to nothing:\n        " % len(dead)
        + "\n        ".join(sorted(set(dead))))
else:
    ok("all %d declared buttons reach some wiring" % n)

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

# THE CHECK MUST TEST THE MODEL THE GAME ACTUALLY USES. The land/sea answer now comes from
# the Natural Earth mask, not the blobs, so this decodes the same base64 the game does. A
# gazetteer pointed at a retired model is worse than no gazetteer at all.
import base64 as _b64
_m = re.search(r'const GLOBE_MASK="([A-Za-z0-9+/=]+)"', s)
_MW, _MH = 720, 360
_mask = _b64.b64decode(_m.group(1)) if _m else None
def _land_mask(lat, lon):
    r = int(round((89.75 - lat)*2));  r = 0 if r < 0 else (_MH-1 if r > _MH-1 else r)
    cc = int(round((lon + 179.75)*2)) % _MW
    idx = r*_MW + cc
    return (_mask[idx >> 3] >> (idx & 7)) & 1

# ASYMMETRIC TOLERANCE, AND THE ASYMMETRY IS THE HONEST PART.
# A WATER point is tested strictly: it was chosen in open sea, so its own cell must be sea,
# and any land there is a real fault. A LAND point is a CITY, and at half a degree - 55 km -
# a port legitimately straddles the boundary: Plymouth sits on a sound, Stockholm on an
# archipelago, Roanoke is a barrier island, Havana and Cartagena are harbours. Their cell
# centre falling in water is a resolution artefact, not a wrong coastline, so a city passes
# if it or an adjoining cell is land.
# This is a weakening and it is written down as one. It does NOT weaken the water half,
# which is the half that catches "add land until it looks right".
def _land_near(la, lo):
    for dla in (-0.5, 0.0, 0.5):
        for dlo in (-0.5, 0.0, 0.5):
            if _land_mask(la + dla, lo + dlo): return True
    return False

_bl = _blobs(s)
if _mask is not None:
    _land = lambda bl, la, lo: bool(_land_near(la, lo))
if _bl is None and _mask is None:
    bad("neither GLOBE_MASK nor GLOBE_LAND found - the globe cannot be checked")
else:
    dry = [n for (n, la, lo) in LAND  if not _land(_bl, la, lo)]
    wet = [n for (n, la, lo) in WATER if (bool(_land_mask(la, lo)) if _mask is not None
                                          else _land(_bl, la, lo))]
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
            # STRICT here, always: the tolerant lambda dilates every coast by a cell and
            # reported 32.2% for a mask whose true figure is 28.8%. An area statistic
            # computed with a fuzzy test is not an area statistic.
            if (bool(_land_mask(la, lo)) if _mask is not None else _land(_bl, la, lo)):
                land_w += w
    print("  note  land covers %.1f%% of the sphere (the Earth is 29.2%%), score %d/%d"
          % (100*land_w/tot_w, okc, tot))

print("\n16. A setting the reader chose survives them closing the game")
# THE VOICE PANEL EXISTS BECAUSE OF A REPORT - "there has to be a better set of voices
# that will work when playing online" - and the one setting it is FOR did not persist.
# The rate chip set S.voicePref.rate and called saveGame(). The voice chip set
# S.voicePref[row.k] and called renderVoices(), which redraws the panel so the choice
# LOOKS taken, and never wrote it to disk. Verified against localStorage before the
# fix: choosing a rate changed the stored blob, choosing a voice did not.
#
# The note on sayRate says S.voicePref is "already in the save whitelist, so this
# persists" - true of the object, and read as true of everything put into it. BEING IN
# THE WHITELIST IS NOT SAVING. It is only permission to be saved, and check 11 - which
# verifies the whitelist - passes either way. This is the check for the other half.
#
# WHAT A DEFERRED BODY COSTS THE READER. A first pass looked for saveGame() anywhere
# inside renderVoices and found one - inside the RATE handler nested within it, which
# runs on a click that has not happened. A save in a body that runs later proves
# nothing about the call that installed it, so handler and timer bodies are blanked
# out before the question is asked. The check was fooled by exactly the shape of the
# bug it was written for.
_persist = set(re.findall(r'S\.([A-Za-z_][A-Za-z0-9_]*)',
                          re.search(r'function saveBlob\(\)\{(.*?)\n\}', s, re.S).group(1)))

def _close(i):
    """The brace that closes the one at i - COUNTING NEITHER STRINGS NOR COMMENTS.
    The first version of this counted raw characters, and in a file that is mostly
    prose in string literals and long comments full of braces, every range it
    returned was wrong. It did not announce itself: the check ran green and reported
    four handlers. It was only caught by taking the fix back OUT of index.html and
    finding that the check still passed - which is the only test of a check that
    means anything. _beats_of has carried a scanner that knows about strings and
    comments since check 14; this is the same one."""
    d, j, instr = 0, i, None
    while j < len(s):
        if not instr:
            if s.startswith("/*", j):
                e = s.find("*/", j + 2); j = len(s) if e < 0 else e + 2; continue
            if s.startswith("//", j):
                e = s.find("\n", j + 2); j = len(s) if e < 0 else e + 1; continue
        c = s[j]
        if instr:
            if c == "\\": j += 2; continue
            if c == instr: instr = None
        elif c in "\"'": instr = c
        elif c == "{": d += 1
        elif c == "}":
            d -= 1
            if d == 0: return j
        j += 1
    return len(s) - 1

_defer = []
for _m in re.finditer(r'(?:onclick|onchange|oninput|ontouchend)\s*=\s*function\s*\([^)]*\)\s*\{', s):
    _defer.append((_m.end() - 1, _close(_m.end() - 1)))
for _m in re.finditer(r'addEventListener\(\s*["\'][a-z]+["\']\s*,\s*function\s*\([^)]*\)\s*\{', s):
    _defer.append((_m.end() - 1, _close(_m.end() - 1)))
for _m in re.finditer(r'set(?:Timeout|Interval)\(\s*function\s*\([^)]*\)\s*\{', s):
    _defer.append((_m.end() - 1, _close(_m.end() - 1)))

# names that are properties holding a function - commit, onBuy, do, when. A handler
# that calls one of these is HANDING OFF, and where it hands off to cannot be read
# here. The wardrobe's Buy button restores S.equip and then calls p.commit(), the
# item's own buy path, which charges the Ink and saves. That is correct and this
# check must not call it a fault.
_cb = set(re.findall(r'\b([A-Za-z_]\w*)\s*:\s*function\s*\(', s))
_cb |= set(re.findall(r'\b([A-Za-z_]\w*)\s*:\s*(?:[A-Za-z_]\w*\.)?(?:on[A-Z]\w*|commit)\b', s))

def _live(a, b):
    """What actually RUNS when this handler runs: the body, minus every deferred body
    inside it, minus comments, minus string contents.

    THE COMMENTS MATTER, AND THIS IS THE THIRD TIME. Blanking deferred bodies alone
    still passed with the bug reinstated - because the comment written ABOVE the fix
    explains the bug and contains the words saveGame(). The check read its own
    documentation as evidence that the code saved. A scanner over this file has to
    ignore prose everywhere it looks, not only where it counts braces: almost all of
    this file is prose, and any pattern matched against the raw text will sooner or
    later match an explanation of itself."""
    out, j, instr = [], a, None
    while j <= b:
        if not instr:
            if s.startswith("/*", j):
                e = s.find("*/", j + 2); e = b if e < 0 else e + 1
                out.append(" " * (min(e, b) - j + 1)); j = min(e, b) + 1; continue
            if s.startswith("//", j):
                e = s.find("\n", j + 2); e = b if e < 0 else e
                out.append(" " * (min(e, b) - j + 1)); j = min(e, b) + 1; continue
        c = s[j]
        if instr:
            out.append(" ")
            if c == "\\": out.append(" "); j += 2; continue
            if c == instr: instr = None
            j += 1; continue
        if c in "\"'":
            instr = c; out.append(" "); j += 1; continue
        out.append(c); j += 1
    txt = list("".join(out))
    for x, y in _defer:
        if x > a and y <= b:
            for k in range(x - a, min(y - a + 1, len(txt))): txt[k] = " "
    return "".join(txt)

def _inner(pos):
    best = None
    for x, y in _defer:
        if x < pos < y and (best is None or (y - x) < (best[1] - best[0])): best = (x, y)
    return best

_lost, _seen_h = {}, set()
for _m in re.finditer(r'S\.([A-Za-z_][A-Za-z0-9_]*)\s*(?:\[[^\]]*\]|\.[A-Za-z_]\w*)?\s*(?:\+|-|\|\|)?=(?!=)', s):
    if _m.group(1) not in _persist: continue
    _h = _inner(_m.start())
    if not _h: continue                       # not in a handler: some other flow saves it
    _seen_h.add(_h)
    _body = _live(_h[0], _h[1])
    if re.search(r'\b(saveGame|checkpoint)\s*\(', _body): continue
    if any(_c.group(1) in _cb for _c in
           re.finditer(r'(?<=[\w\)\]])\.\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(', _body)): continue
    _lost[_h] = (s[:_m.start()].count("\n") + 1, _m.group(1))
if _lost:
    bad("%d handler(s) change a saved setting and never save it:\n        " % len(_lost)
        + "\n        ".join("S.%s written at line %d, no save in that handler" % (k, ln)
                            for ln, k in sorted(_lost.values())))
else:
    ok("all %d handlers that write saved state either save or hand off" % len(_seen_h))


print("\n17. The muster can be reached from every state a player can get into")
# THE OLDEST RULE IN THE ADVENTURE GENRE - no sequence of reasonable actions may leave
# the game unfinishable - and Chapter II broke it. The survey hands out twelve days; the
# passage to each of three sites costs one and each of its three findings costs one, so
# seeing everything costs exactly 3 + 9 = 12 and there is no slack at all. Sail about
# looking at the chart, which is what a curious twelve-year-old does, and you could
# arrive at nought daylight holding fewer than the three findings the scrivener wants,
# with both doSurvey and travelTo refusing. The chapter could not then be finished.
#
# travelTo now refuses a passage that would put the muster out of reach. This walks
# EVERY reachable state to prove it, rather than trusting that sentence - and it reads
# the budget, the costs, the finding counts and the threshold out of the game so the
# proof cannot drift away from the thing it is proving.
_sites, _cost, _nsv = [], {}, {}
_m = re.search(r'const SITES\s*=\s*\{', s)
_i = _m.end() - 1
_d = 0; _j = _i; _q = None
while _j < len(s):
    if not _q and s.startswith("/*", _j):
        _e = s.find("*/", _j + 2); _j = len(s) if _e < 0 else _e + 2; continue
    _c = s[_j]
    if _q:
        if _c == "\\": _j += 2; continue
        if _c == _q: _q = None
    elif _c in "\"'": _q = _c
    elif _c == "{": _d += 1
    elif _c == "}":
        _d -= 1
        if _d == 0: break
    _j += 1
_blk = s[_i:_j + 1]
_ends = [m.start() for m in re.finditer(r'\n  [a-z]+:\{', _blk)] + [len(_blk)]
for _k, _mm in enumerate(re.finditer(r'\n  ([a-z]+):\{', _blk)):
    _name = _mm.group(1)
    _seg = _blk[_mm.start():_ends[_k + 1]]
    _sites.append(_name)
    _cm = re.search(r'\bcost:\s*([0-9]+)', _seg)
    _cost[_name] = int(_cm.group(1)) if _cm else 0
    _nsv[_name] = len(re.findall(r'\{k:"', _seg.split("surveys:")[1])) if "surveys:" in _seg else 0
_budget = sum(1 + _nsv[k] for k in _sites if not re.search(
    r'\n  ' + k + r':\{[^\n]*home:\s*true', _blk))
_need = int(re.search(r'const MUSTER_FINDINGS=([0-9]+)', s).group(1))
# AND THE MUSTER WANTS THEM FROM MORE THAN ONE PLACE. Read, not assumed - if the game
# stops requiring a spread this walk stops requiring one too.
_nsit = int(re.search(r'const MUSTER_SITES=([0-9]+)', s).group(1))
_home = [k for k in _sites if re.search(r'\n  ' + k + r':\{[^\n]*home:\s*true', _blk)]
_start = _home[0] if _home else _sites[0]

def _open(found):
    return (sum(found.values()) >= _need
            and sum(1 for v in found.values() if v > 0) >= _nsit)

def _days_to(key, found):
    """Exact, by the same search the game does - three findings from two sites has four
    cases and an arithmetic shortcut got two of them wrong."""
    if _open(found): return 0
    seen, q, head = set(), [(0, key, tuple(sorted(found.items())))], 0
    while head < len(q):
        d, at, f = q[head]; head += 1
        if (at, f) in seen: continue
        seen.add((at, f))
        fd = dict(f)
        if _open(fd): return d
        if fd.get(at, 0) < _nsv.get(at, 0):
            nf = dict(fd); nf[at] = nf.get(at, 0) + 1
            q.append((d + 1, at, tuple(sorted(nf.items()))))
        # (the search itself is unguarded - it is asking what is POSSIBLE, not what the
        #  guard permits; the guard is applied in _moves, to the player's actions)
        for j in _sites:
            if j == at: continue
            q.append((d + _cost[j], j, f))
    return 10 ** 9

def _reach(days, key, found):
    return days >= _days_to(key, found)

# ---- AND WHETHER THE GAME ACTUALLY HAS THE GUARD IS READ, NOT ASSUMED ----
# The first version of this walked the state space with the guard hard-coded into the
# Python. Disabling the guard in index.html left the check green, because the check was
# proving a property of its own model. Exactly the fault check 16 was written for,
# wearing a different coat. So the guard is applied to the walk only if travelTo really
# contains it, in code rather than in a comment - and if it does not, the walk goes
# unguarded and the dead ends come back.
_tv = re.search(r'function\s+travelTo\s*\([^)]*\)\s*\{', s)
_tb = s[_tv.end():_tv.end() + 4000] if _tv else ""
_tb = re.sub(r'/\*.*?\*/', ' ', _tb, flags=re.S)          # comments are not code
_guarded = "if(!gateReachable(surveyDays()-cost,key))" in _tb.replace(" ", "")
_sv = re.search(r'function\s+doSurvey\s*\([^)]*\)\s*\{', s)
_sb = re.sub(r'/\*.*?\*/', ' ', s[_sv.end():_sv.end() + 2500], flags=re.S) if _sv else ""
_surveyguard = "if(!gateReachable(surveyDays()-1,d.site,key))" in _sb.replace(" ", "")

def _moves(st):
    days, key, found = st[0], st[1], dict(st[2])
    out = []
    if found.get(key, 0) < _nsv.get(key, 0) and days >= 1:
        nf = dict(found); nf[key] = nf.get(key, 0) + 1
        # THE SAME GUARD APPLIES TO A FINDING. Under a two-site gate a finding no longer
        # always advances you, so doSurvey asks the same question travelTo does.
        if not _surveyguard or _reach(days - 1, key, nf):
            out.append((days - 1, key, tuple(sorted(nf.items()))))
    for j in _sites:
        if j == key: continue
        c = _cost[j]
        if c and days < c: continue
        if _guarded and not _reach(days - c, j, found): continue
        out.append((days - c, j, st[2]))
    return out

_init = (_budget, _start, tuple(sorted({k: 0 for k in _sites}.items())))
_seen, _stack, _dead, _tight = {_init}, [_init], [], None
while _stack:
    st = _stack.pop()
    days, key, found = st[0], st[1], dict(st[2])
    if _open(found): continue                           # muster already open
    mv = _moves(st)
    if not mv:
        _dead.append(st)
        continue
    if _tight is None or days < _tight[0]: _tight = st
    for n in mv:
        if n not in _seen:
            _seen.add(n); _stack.append(n)
if _dead:
    bad("%d state(s) from which the muster can never be reached, e.g. %d day(s) at %s "
        "holding %d finding(s)" % (len(_dead), _dead[0][0], _dead[0][1],
                                   sum(dict(_dead[0][2]).values())))
else:
    ok("%d reachable states walked, %d days from %s, %d findings from %d sites wanted "
       "- no dead end%s"
       % (len(_seen), _budget, _start, _need, _nsit,
          "" if (_guarded and _surveyguard) else
          " (guards: travelTo %s, doSurvey %s)" % ("yes" if _guarded else "NO",
                                                   "yes" if _surveyguard else "NO")))
    if _tight:
        print("  note  tightest survivable state: %d day(s) at %s holding %d finding(s)"
              % (_tight[0], _tight[1], sum(dict(_tight[2]).values())))


print("\n19. A world that replaces the ground says whether it has a hull")
# csRoom() measures how much room the camera has by asking the SHIP's half-beam at that
# point, and it was asked in every world. On the strand at Cape Henry it returned -34.57 -
# forty-six feet off a centreline belonging to a vessel that is not in the scene - so the
# yaw search picked between twenty equally impossible angles on a tiebreak and the pull-in
# loop dragged every cutscene shot in the chapter down to its 4.5 floor. The execution
# framed 9.79 to 17.06 feet above the sand with the condemned man's head at 5.47: he was
# not in the picture, and the heights were never the problem.
#
# WORLD.hull carries the answer. The rule that keeps it true is positional: the function
# that replaces WORLD.ground is the one that has left the ship, so it must set WORLD.hull
# in the same breath. That is a convention, and a convention nobody checks is a comment.
_gsets = [m for m in re.finditer(r'WORLD\.ground\s*=', s)]
_missing = []
for m in _gsets:
    # the same statement, or within the next four lines of it
    seg = s[m.start(): m.start() + 400]
    seg = seg[: nth_newline(seg, 4)]
    if not re.search(r'WORLD\.hull\s*=', seg):
        _missing.append(s[:m.start()].count("\n") + 1)
if not _gsets:
    bad("no WORLD.ground assignment found at all - this check has lost its subject")
elif _missing:
    bad("%d place(s) set WORLD.ground without saying whether there is a hull "
        "(line%s %s) - csRoom will measure a ship that is not there"
        % (len(_missing), "" if len(_missing) == 1 else "s",
           ", ".join(str(n) for n in _missing)))
else:
    ok("all %d worlds that set their own ground also declare WORLD.hull" % len(_gsets))

# and the guard itself has to still be in csRoom, or the flag is decoration
_cs = body_of(s, "csRoom")
if _cs is None:
    bad("csRoom not found")
elif not re.search(r'if\s*\(\s*!\s*WORLD\.hull\s*\)\s*return', _cs):
    bad("csRoom no longer consults WORLD.hull - every hull-less world is back to "
        "measuring the ship's beam")
else:
    ok("csRoom asks WORLD.hull before it measures a beam")


print("\n20. A change to the game carries a new build id")
# THE UPDATER IS ONLY AS GOOD AS THE THING IT COMPARES. index.html carries BUILD;
# version.txt carries the same id; the page fetches version.txt with cache no-store and
# reloads itself when the two disagree. Check 10 proves they agree with EACH OTHER, and
# they agreed perfectly through four commits in one afternoon that changed the impact
# mark, the cutscene camera, the execution and the survey - because I never ran
# tools/stamp.py. Every player's updater fetched version.txt, read the id it already had,
# and correctly concluded it was current. The fixes were on the server and nobody could
# get them, and the bug was reported back to me as "is this pushed?".
#
# So: if index.html is staged with changes, its BUILD must not be the one in HEAD. That is
# the whole rule, and it is the one check 10 cannot make, because a stale pair is a
# perfectly consistent pair.
_head_html = None
if shutil.which("git") is not None:
    _r = subprocess.run(["git", "show", "HEAD:index.html"], capture_output=True, cwd=ROOT)
    if _r.returncode == 0:
        _head_html = _r.stdout.decode("utf-8", "replace")
    _st = subprocess.run(["git", "diff", "--cached", "--name-only"],
                         capture_output=True, cwd=ROOT)
    _staged_names = _st.stdout.decode("utf-8", "replace").split() if _st.returncode == 0 else []
else:
    _staged_names = []

if _head_html is None:
    print("  skip  no git, or no HEAD to compare against")
elif "index.html" not in _staged_names:
    ok("index.html is not staged - nothing to deploy, nothing to stamp")
else:
    _new = staged("index.html")
    _old_id = stamp_pair(_head_html, "x")[0]
    _new_id = stamp_pair(_new, "x")[0] if _new else None
    if _new_id is None:
        bad("the staged index.html has no `const BUILD=\"...\"` to stamp")
    elif _new_id == _old_id:
        bad("index.html has changed but still says BUILD %s - run `python tools/stamp.py` "
            "or every copy already out there will decide it is up to date and keep "
            "serving the old game" % _new_id)
    else:
        ok("staged index.html carries a new build id (%s, was %s)" % (_new_id, _old_id))


print("\n21. The patch notes are not older than the build")
# TWICE NOW the player has been the one to notice a release. First version.txt was never
# re-stamped, so the auto-updater had nothing to find (check 20). Then the updater worked,
# the new build arrived, and the Patch Notes screen still said "4 August 2026 - latest"
# through ten changes across two sittings - so the game was current and told him it was
# not. Both are the same fault wearing different clothes: the code shipped and the thing
# that REPORTS the code to a human did not.
#
# The rule is deliberately slack. Not every commit earns a note, and a check that demanded
# one would just teach me to write empty ones. But a build three days newer than the
# newest note means a release went out unannounced, and that is worth stopping for.
_MONTHS = {"january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
           "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
           "december": 12}
_pn = re.search(r'const PATCH_NOTES=\[\s*\{when:"([^"]*)"', s)
_bd = re.search(r'const BUILD="(\d{4})(\d{2})(\d{2})-', s)
if not _pn:
    bad("no PATCH_NOTES array, or its first entry has no `when`")
elif not _bd:
    bad("no build stamp to compare the notes against")
else:
    _wm = re.match(r'\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})', _pn.group(1))
    if not _wm or _wm.group(2).lower() not in _MONTHS:
        bad("the newest patch note is dated %r, which this check cannot read - it wants "
            "`D Month YYYY`" % _pn.group(1))
    else:
        import datetime
        _note = datetime.date(int(_wm.group(3)), _MONTHS[_wm.group(2).lower()],
                              int(_wm.group(1)))
        _build = datetime.date(int(_bd.group(1)), int(_bd.group(2)), int(_bd.group(3)))
        _gap = (_build - _note).days
        if _gap > 3:
            bad("the build is %s and the newest patch note is %s - %d days apart. A "
                "release has gone out that the game never told anybody about; add an "
                "entry to the TOP of PATCH_NOTES" % (_build, _note, _gap))
        elif _gap < 0:
            print("  note  the newest patch note (%s) is dated after the build (%s)"
                  % (_note, _build))
        else:
            ok("newest note %s, build %s - %d day(s) apart" % (_note, _build, _gap))


print("\n" + ("PASS" if not fail else "FAILED %d check(s)" % len(fail)))
sys.exit(0 if not fail else 1)
