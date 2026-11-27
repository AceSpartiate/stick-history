#!/usr/bin/env python3
"""shot_qa.py - a local vision model looks at the game's captures first, so Claude only has to
look at the doubtful ones.

    python tools/shot_qa.py <png|folder>... [--expect "<what should be in frame>"] [--model gemma4:26b-a4b-it-qat]
                                           [--out tools/shots/_qa.md] [--since <minutes>]

Each capture is asked one fixed checklist (the hard faults this project keeps finding in its own
renders: a camera inside a wall, a black or blank frame, a subject cut off, figures floating or
sunk, props through walls). The answer is JSON: verdict ok | doubt | fault, and the faults seen.
Writes a report, worst first, and prints the names to look at. A verdict is a reading aid, not a
pass: anything but "ok" goes to a human (or to Claude) to look at.

Owner, 2026-11-27: "Automatic visual QA". LOCAL_AI.md rules kept: Ollama is called directly at
127.0.0.1 (never inside a Comfy() block), the batch calls comfy.wait_for_4060ti() before loading,
and it waits while any OTHER model is loaded rather than load beside it. gemma4 is the default
because it caught every planted fault in the church cartoon QA where qwen3-vl missed several.
"""
import argparse, base64, glob, json, os, sys, time
import requests

sys.path.insert(0, r'E:\VN-Tools\asset-toolkit')
OLLAMA = 'http://127.0.0.1:11434'

PROMPT = """You are checking a frame rendered by a low-poly 3D history game for middle-school students.
Simple blocky stick figures, flat colours and plain textures are the intended art style: do NOT report them.
Report only HARD FAULTS:
- black, blank or nearly empty frame;
- the camera is inside or right against geometry, so a wall, planks, a roof or a trunk fills most of the view;
- the obvious subject (people, a building, an object) is cut off by the frame edge or hidden behind something close;
- a person floats above the ground or is sunk into it to the knees or more;
- a person or object passes through a wall, a building or another object;
- something clearly broken: stretched shards, a surface rendered black because it faces the wrong way, flickering stripes.
{expect}
Answer with JSON only: {{"verdict": "ok" | "doubt" | "fault", "faults": ["short description", ...], "subject": "what the frame shows, in under 12 words"}}.
"ok" means no hard fault. Use "doubt" if you are not sure."""


def loaded():
    try:
        return [m.get('name') for m in requests.get(OLLAMA + '/api/ps', timeout=10).json().get('models', [])]
    except Exception:
        return []


def wait_turn(model, wait_min=30):
    try:
        import comfy
        comfy.wait_for_4060ti(quiet=True)
    except Exception as e:  # the toolkit is advisory here; Ollama itself still works
        print('  (comfy.wait_for_4060ti unavailable:', e, ')', flush=True)
    t0, said = time.time(), False
    while True:
        other = [m for m in loaded() if m and m != model]
        if not other:
            return
        if not said:
            print('  waiting: Ollama has', ', '.join(other), 'loaded (one model at a time)', flush=True)
            said = True
        if time.time() - t0 > wait_min * 60:
            sys.exit('shot_qa: another model stayed loaded; not run')
        time.sleep(15)


def ask(model, path, expect):
    img = base64.b64encode(open(path, 'rb').read()).decode()
    body = {'model': model, 'stream': False, 'format': 'json', 'think': False,
            'options': {'temperature': 0, 'num_ctx': 8192},
            'messages': [{'role': 'user', 'images': [img],
                          'content': PROMPT.format(expect=('Expected in frame: ' + expect) if expect else '')}]}
    r = requests.post(OLLAMA + '/api/chat', json=body, timeout=600)
    r.raise_for_status()
    txt = r.json()['message']['content']
    try:
        d = json.loads(txt)
    except Exception:
        d = {'verdict': 'doubt', 'faults': ['unparsed answer: ' + txt[:120]], 'subject': ''}
    if d.get('verdict') not in ('ok', 'doubt', 'fault'):
        d['verdict'] = 'doubt'
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('paths', nargs='+')
    ap.add_argument('--expect', default='')
    ap.add_argument('--model', default='gemma4:26b-a4b-it-qat')
    ap.add_argument('--out', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'shots', '_qa.md'))
    ap.add_argument('--since', type=float, default=0, help='only files changed in the last N minutes')
    a = ap.parse_args()
    files = []
    for p in a.paths:
        files += sorted(glob.glob(os.path.join(p, '*.png'))) if os.path.isdir(p) else [p]
    if a.since:
        cut = time.time() - a.since * 60
        files = [f for f in files if os.path.getmtime(f) >= cut]
    if not files:
        sys.exit('shot_qa: no captures')
    wait_turn(a.model)
    rows, order = [], {'fault': 0, 'doubt': 1, 'ok': 2}
    for i, f in enumerate(files):
        t = time.time()
        d = ask(a.model, f, a.expect)
        rows.append((order[d['verdict']], os.path.basename(f), d))
        print(f'{i + 1}/{len(files)} {d["verdict"]:5} {os.path.basename(f)}  {"; ".join(d.get("faults") or [])}  ({time.time() - t:.0f}s)', flush=True)
    rows.sort(key=lambda r: (r[0], r[1]))
    with open(a.out, 'w', encoding='utf-8') as fh:
        fh.write(f'# Shot QA ({a.model}): {sum(r[0] < 2 for r in rows)} of {len(rows)} to look at\n\n')
        fh.write('| verdict | shot | faults | subject |\n|---|---|---|---|\n')
        for _, n, d in rows:
            fh.write(f'| {d["verdict"]} | {n} | {"; ".join(d.get("faults") or [])} | {d.get("subject", "")} |\n')
    look = [n for o, n, _ in rows if o < 2]
    print('LOOK AT:', ' '.join(look) if look else 'nothing', flush=True)


if __name__ == '__main__':
    main()
