#!/usr/bin/env python3
"""asset_job.py - a local model models Stick History's 3D assets in Blender; Claude only reviews the result.

    python tools/blender/asset_job.py tools/blender/fort_specs.md [--only name,name] [--tries 12] [--reviews 0]
                                      [--model qwen3.8:27b] [--previews <dir>] [--notes "<text or file>"]

--notes revises: the named assets' saved conversation continues with the director's notes, and the model keeps
fixing (Blender checks, then its own look at the renders) until its review passes or --tries runs out.
--reviews 0 means review until it passes. The model stays loaded (keep_alive 2h); Blender runs beside it.

For each "## name" section of the spec file:
  1. The model (qwen3.8:27b, Ollama) writes build() using tools/blender/kit.py's helpers.
  2. Blender (run_asset.py, through gpu_job.py as a light job) runs it, checks it (errors, Part names, triangle
     budget, floating), exports assets/<dir>/<name>.glb and renders two views. Problems go back to the model.
  3. The same model LOOKS at its renders against the spec and lists defects; up to --reviews rounds of fixes.
  4. The accepted script is kept as the asset's source: tools/blender/<dir>/<name>.py.
None of the loop costs Claude tokens. Section header line under "## name":
    out: fort/brush_fence.glb | nodes: a,b,c | budget: 8000 | grounded: yes
2026-11-09.
"""
import base64, json, os, re, subprocess, sys, time, urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
TOOLKIT = r'E:\VN-Tools\asset-toolkit'
BLENDER = r'E:\VN-Tools\blender\blender.exe'
OLLAMA = 'http://127.0.0.1:11434/api/chat'
BANNED = re.compile(r'\b(import|__import__|exec|eval|open|subprocess|os\.|sys\.|shutil|bpy\.ops)\b')


def kit_doc():
    src = open(os.path.join(HERE, 'kit.py'), encoding='utf-8').read()
    out = []
    for m in re.finditer(r'^( *)def (\w+)\((.*?)\):\n\s+"""(.*?)"""', src, re.S | re.M):
        if m.group(2).startswith('_') or m.group(2) == 'realize':
            continue
        owner = 'Part.' if m.group(1) else ''
        args = m.group(3).replace('self, ', '').replace('self', '')
        out.append(f'{owner}{m.group(2)}({args})\n    ' + m.group(4).strip().replace('\n', '\n    '))
    return '\n'.join(out)


PROMPT = """You are modelling a 3D asset for a low-poly, vertex-coloured history game for 6th-8th graders
(Jamestown, 1607). Write a Python function build() that builds it with these helpers (already defined; do not
import anything or redefine them). Units are FEET, Blender Z is up, the ground is z=0.

{kit}

Also available: math, Vector (mathutils). Colours are sRGB hex strings like '#b08a5a'.

STYLE (this matters most):
- Low-poly but with FORM: round timber is Part.log (8 sides; 5-6 for small sticks) and tapers; never a box for a
  round thing. Posts lean slightly and vary in height and width; nothing is a grid of identical copies - use a
  seeded R = rng(<number>) for every variation.
- Things that stand on the ground start slightly below it (z=-0.2) so they never float.
- Watch the triangle budget: a log with caps is about 2*sides+2*(sides-2) triangles.
- Call occlude() once at the very end of build().
- Make exactly the Parts named in the request, no others. Every Part must have faces.

THE ASSET: {name}
{spec}

Reply with ONE ```python block containing build() and any small helper functions it needs. No prose."""

REVIEW = """These are two renders of the asset you just built (grey studio light, brown ground plate).
The request was:

{spec}

Blender has already checked the parts mechanically and they all exist: {parts}. The renders show ALL of them
together, assembled, so several parts forming one continuous whole is correct - never report a part as missing.

List concrete, visible defects against the request and the style rules (wrong shape or proportion, missing
pieces, parts floating or stuck through each other, boxes where round timber was asked for, identical repeated
copies, wrong orientation). Ignore lighting, colour exactness and the ground plate. Reply as JSON:
{{"pass": true/false, "defects": ["...", "..."]}} with pass=true only if nothing important is wrong."""


def ask(messages, model, fmt=None, think=True):
    try:
        sys.path.insert(0, TOOLKIT)
        import comfy
        comfy.wait_for_4060ti()
    except Exception:
        pass
    body = {'model': model, 'stream': False, 'messages': messages, 'think': think, 'keep_alive': '2h',
            'options': {'temperature': 0.3, 'num_ctx': 32768}}
    if fmt:
        body['format'] = fmt
    req = urllib.request.Request(OLLAMA, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    # The GPU arbiter restarts the model server when Parsec or a game comes and goes (game mode <-> agent mode),
    # which drops the request in flight. Found 2026-11-09: six assets lost in 17 minutes. Wait it out and resend.
    for attempt in range(60):
        try:
            with urllib.request.urlopen(req, timeout=1800) as r:
                return json.loads(r.read())['message']['content']
        except (urllib.error.URLError, ConnectionError, OSError) as e:
            if attempt == 59:
                raise
            print(time.strftime('%H:%M:%S'), f'model server unavailable ({e}); retrying in 30 s', flush=True)
            time.sleep(30)


def extract(text):
    m = re.search(r'```(?:python)?\n(.*?)```', text, re.S)
    return (m.group(1) if m else text).strip() + '\n'


def free_mib():
    """Free VRAM per card, from nvidia-smi."""
    try:
        out = subprocess.run(['nvidia-smi', '--query-gpu=memory.free', '--format=csv,noheader,nounits'],
                             capture_output=True, text=True, timeout=20).stdout
        return [int(x) for x in out.split()]
    except Exception:
        return [99999]


def run(script, glb, meta, rdir):
    """Blender check + export + Workbench preview. Runs DIRECTLY, beside the loaded model, not through the comfy
    lease: the owner's call on 2026-11-09 ("if our vram can handle it, I'd rather let qwen 3.8 27b drive the modeling
    live"). qwen3.8 sits across both cards at about 12.5 + 8.3 GB of 16 + 16, and a Workbench preview of a few
    thousand triangles needs a few hundred MB, so the guard is a free-VRAM check, not a lease. A heavy job that
    takes the cards (a ComfyUI paint run, a game) shows up here as no free memory, and this waits."""
    while max(free_mib()) < 1500:
        time.sleep(30)
    rep = os.path.join(rdir, 'report.json')
    if os.path.exists(rep):
        os.remove(rep)
    args = [script, glb, rep]
    if meta.get('nodes'):
        args += ['--nodes', meta['nodes']]
    if meta.get('budget'):
        args += ['--budget', meta['budget']]
    if meta.get('grounded', 'yes').startswith('y'):
        args.append('--grounded')
    args += ['--render', rdir]
    p = subprocess.run([BLENDER, '-b', '--factory-startup', '--python', os.path.join(HERE, 'run_asset.py'), '--', *args],
                       capture_output=True, text=True, timeout=1200)
    if not os.path.exists(rep):
        return {'ok': False, 'problems': ['Blender crashed: ' + (p.stdout + p.stderr)[-600:]]}
    return json.load(open(rep, encoding='utf-8'))


def parse_specs(path):
    out = []
    for block in re.split(r'^## ', open(path, encoding='utf-8').read(), flags=re.M)[1:]:
        name, _, rest = block.partition('\n')
        head, _, body = rest.strip().partition('\n')
        meta = {k.strip(): v.strip() for k, v in (kv.split(':', 1) for kv in head.split('|'))}
        out.append((name.strip(), meta, body.strip()))
    return out


def job(name, meta, spec, a, log):
    rdir = os.path.join(a['previews'], name)
    os.makedirs(rdir, exist_ok=True)
    glb = os.path.join(ROOT, 'assets', meta['out'])
    src_dir = os.path.join(HERE, os.path.dirname(meta['out']))
    os.makedirs(src_dir, exist_ok=True)
    src = os.path.join(src_dir, name + '.py')
    req = PROMPT.format(kit=kit_doc(), name=name, spec=spec + f"\n\nParts to make: {meta.get('nodes')}. "
                        f"Triangle budget: {meta.get('budget')}.")
    chat = os.path.join(rdir, 'chat.json')
    if a.get('notes'):
        # REVISE: carry on the same conversation with the director's notes. Without a saved chat, start from the
        # current source so the model edits what exists rather than starting over.
        if os.path.exists(chat):
            msgs = json.load(open(chat, encoding='utf-8'))
        else:
            msgs = [{'role': 'user', 'content': req}]
            if os.path.exists(src):
                msgs.append({'role': 'assistant', 'content': '```python\n' + open(src, encoding='utf-8').read() + '```'})
        msgs.append({'role': 'user', 'content': 'The art director reviewed your latest version. Keep what works and '
                     'fix this, then send the whole build() again:\n' + a['notes']})
    else:
        msgs = [{'role': 'user', 'content': req}]
    reviews, t0, passed = 0, time.time(), False
    k0 = len([f for f in os.listdir(rdir) if f.startswith('try')])
    for k in range(k0 + 1, k0 + a['tries'] + 1):
        reply = ask(msgs, a['model'])
        code = extract(reply)
        msgs.append({'role': 'assistant', 'content': '```python\n' + code + '```'})
        json.dump(msgs, open(chat, 'w', encoding='utf-8'))
        tmp = os.path.join(rdir, f'try{k}.py')
        open(tmp, 'w', encoding='utf-8').write(code)
        bad = sorted({m.group(0) for m in BANNED.finditer(code)})
        rep = {'ok': False, 'problems': ['not allowed in the script: ' + ', '.join(bad)]} if bad else run(tmp, glb, meta, rdir)
        log(f'{name} try {k}: ok={rep.get("ok")} tris={rep.get("tris")} problems={len(rep.get("problems", []))}')
        if not rep.get('ok'):
            msgs.append({'role': 'user', 'content': 'Blender reported these problems; fix them and send the whole '
                         'build() again:\n- ' + '\n- '.join(rep['problems'])})
            continue
        open(src, 'w', encoding='utf-8').write(code)  # the best passing version so far is the source
        if a['reviews'] and reviews >= a['reviews']:
            break
        imgs = [base64.b64encode(open(p, 'rb').read()).decode() for p in rep['renders']]
        try:
            rv = json.loads(ask([{'role': 'user', 'content': REVIEW.format(spec=spec, parts=', '.join(f'{k} ({v} triangles)' for k, v in rep.get('nodes', {}).items())), 'images': imgs}], a['model'],
                                fmt={'type': 'object', 'properties': {'pass': {'type': 'boolean'},
                                     'defects': {'type': 'array', 'items': {'type': 'string'}}},
                                     'required': ['pass', 'defects']}, think=False))
        except Exception as e:
            log(f'{name} review failed: {e}')
            break
        reviews += 1
        log(f'{name} review {reviews}: pass={rv["pass"]} {rv["defects"][:6]}')
        if rv['pass'] or not rv['defects']:
            passed = True
            break
        msgs.append({'role': 'user', 'content': 'It builds. Looking at the renders (two whole views and a close-up), '
                     'fix these and send the whole '
                     'build() again:\n- ' + '\n- '.join(rv['defects'][:8])})
        json.dump(msgs, open(chat, 'w', encoding='utf-8'))
    ok = os.path.exists(src) and os.path.exists(glb)
    final = run(src, glb, meta, rdir) if ok else {}
    log(f'{name} DONE ok={ok} {"PASSED its own review" if passed else "GAVE UP - needs the director"} tris={final.get("tris")} bytes={final.get("bytes")} nodes={final.get("nodes")} '
        f'{time.time() - t0:.0f}s')
    return ok


def main():
    argv = sys.argv[1:]
    opt = lambda k, d=None: argv[argv.index(k) + 1] if k in argv else d
    a = {'tries': int(opt('--tries', 12)), 'reviews': int(opt('--reviews', 0)), 'model': opt('--model', 'qwen3.8:27b'),
         'previews': opt('--previews', os.path.join(HERE, '_previews')), 'notes': opt('--notes')}
    if a['notes'] and os.path.exists(a['notes']):
        a['notes'] = open(a['notes'], encoding='utf-8').read()
    only = set((opt('--only') or '').split(',')) - {''}
    logf = open(os.path.join(a['previews'], 'job.log') if os.path.isdir(a['previews']) else os.devnull, 'a')

    def log(s):
        line = time.strftime('%H:%M:%S ') + s
        print(line, flush=True)
        logf.write(line + '\n')
        logf.flush()

    for name, meta, spec in parse_specs(argv[0]):
        if only and name not in only:
            continue
        try:
            job(name, meta, spec, a, log)
        except Exception as e:
            log(f'{name} FAILED: {e}')


if __name__ == '__main__':
    main()
