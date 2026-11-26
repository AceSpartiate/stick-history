#!/usr/bin/env python3
"""build_one.py - build one fort asset from its script in tools/blender/fort/, using the header line of its spec in
fort_specs.md, and put the three Workbench views on one contact sheet.

    python tools/blender/build_one.py <name> [--specs ch2_specs.md] [--views <dir>]

Prints the report (problems, triangles, bytes) and the sheet's path. Light GPU work (Workbench), no lease:
LOCAL_AI.md, "Exception: Blender previews".
"""
import json, os, subprocess, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
BLENDER = r'E:\VN-Tools\blender\blender.exe'
sys.path.insert(0, HERE)
from asset_job import parse_specs  # noqa: E402

name = sys.argv[1]
views = sys.argv[sys.argv.index('--views') + 1] if '--views' in sys.argv else os.path.join(HERE, '_views', name)
os.makedirs(views, exist_ok=True)
specs = sys.argv[sys.argv.index('--specs') + 1] if '--specs' in sys.argv else 'fort_specs.md'
meta = {n: m for n, m, _ in parse_specs(os.path.join(HERE, specs))}[name]
glb = os.path.join(ROOT, 'assets', meta['out'])
rep = os.path.join(views, 'report.json')
args = [os.path.join(HERE, os.path.dirname(meta['out']), name + '.py'), glb, rep]   # the script sits by its out folder's name
if meta.get('nodes'):
    args += ['--nodes', meta['nodes']]
if meta.get('budget'):
    args += ['--budget', meta['budget']]
if meta.get('grounded', 'yes').startswith('y'):
    args.append('--grounded')
args += ['--render', views]
p = subprocess.run([BLENDER, '-b', '--factory-startup', '--python', os.path.join(HERE, 'run_asset.py'), '--', *args],
                   capture_output=True, text=True, timeout=1200)
if not os.path.exists(rep):
    print('Blender crashed:', (p.stdout + p.stderr)[-1500:])
    sys.exit(1)
r = json.load(open(rep))
print(json.dumps({k: r[k] for k in ('ok', 'problems', 'tris', 'nodes') if k in r}), 'bytes', r.get('bytes'))
ims = [Image.open(f) for f in r.get('renders', [])]
if ims:
    w, h = ims[0].size
    sheet = Image.new('RGB', (w, h * len(ims)))
    for i, im in enumerate(ims):
        sheet.paste(im, (0, h * i))
    out = os.path.join(views, 'sheet.jpg')
    sheet.resize((w * 2 // 3, h * len(ims) * 2 // 3)).save(out, quality=85)
    print('sheet', out)
