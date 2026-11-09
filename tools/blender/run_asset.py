"""run_asset.py - runs inside Blender: build one asset from a model-written script, check it, export it, render it.

    blender -b --factory-startup --python tools/blender/run_asset.py -- <script.py> <out.glb> <report.json> \
        [--nodes a,b,c] [--budget N] [--grounded] [--render <dir>]

The script defines build(); kit.py's names (Part, rng, lin, occlude, Vector, math) are in scope.
Report: {"ok", "problems":[...], "nodes":{name:tris}, "tris", "bbox":[min,max] (feet, Blender Z-up),
"renders":[png...]}. Problems are what goes back to the model; they cost no Claude tokens.
"""
import json, math, os, sys, traceback
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
argv = sys.argv[sys.argv.index('--') + 1:]
script, out_glb, report = argv[0], argv[1], argv[2]
opt = lambda k: argv[argv.index(k) + 1] if k in argv else None
nodes_want = [n for n in (opt('--nodes') or '').split(',') if n]
budget = int(opt('--budget') or 0)
grounded = '--grounded' in argv
rdir = opt('--render')
rep = {'ok': False, 'problems': [], 'nodes': {}, 'tris': 0, 'bbox': None, 'renders': []}


def done():
    json.dump(rep, open(report, 'w'), indent=1)
    sys.exit(0)


for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)
ns = {'__name__': 'asset'}
try:
    exec(open(os.path.join(HERE, 'kit.py'), encoding='utf-8').read(), ns)
    exec(open(script, encoding='utf-8').read(), ns)
    if 'build' not in ns:
        rep['problems'].append('the script defines no build() function')
        done()
    ns['build']()
    objs = ns['realize']()
except Exception:
    tb = traceback.format_exc().splitlines()
    rep['problems'].append('Python error while building:\n' + '\n'.join(tb[-8:]))
    done()

if not objs:
    rep['problems'].append('build() made no Part with any faces')
    done()
lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
for ob in objs:
    me = ob.data
    t = sum(len(p.vertices) - 2 for p in me.polygons)
    rep['nodes'][ob.name] = t
    rep['tris'] += t
    if t == 0:
        rep['problems'].append(f'Part "{ob.name}" has no faces')
    zs = [v.co.z for v in me.vertices]
    if me.vertices:
        for v in me.vertices:
            for k in range(3):
                lo[k], hi[k] = min(lo[k], v.co[k]), max(hi[k], v.co[k])
        if grounded and min(zs) > 0.5:
            rep['problems'].append(f'Part "{ob.name}" floats: its lowest point is z={min(zs):.2f} ft; '
                                   'grounded things must touch z=0')
        if min(zs) < -6 and grounded:
            rep['problems'].append(f'Part "{ob.name}" reaches z={min(zs):.2f} ft, far below the ground')
rep['bbox'] = [list(lo), list(hi)]
names = {o.name for o in objs}
for n in nodes_want:
    if n not in names:
        rep['problems'].append(f'missing Part named "{n}" (Parts made: {sorted(names)})')
extra = names - set(nodes_want) if nodes_want else set()
if extra:
    rep['problems'].append(f'unexpected Part names {sorted(extra)}; use exactly {nodes_want}')
if budget and rep['tris'] > budget:
    rep['problems'].append(f'{rep["tris"]} triangles is over the budget of {budget}; use fewer sides or pieces')

if not rep['problems']:
    os.makedirs(os.path.dirname(out_glb) or '.', exist_ok=True)
    bpy.ops.object.select_all(action='SELECT')
    try:
        bpy.ops.export_scene.gltf(filepath=out_glb, export_format='GLB', use_selection=True, export_yup=True,
                                  export_apply=True, export_texcoords=False, export_normals=True,
                                  export_materials='NONE', export_vertex_color='ACTIVE', export_animations=False)
    except TypeError:
        bpy.ops.export_scene.gltf(filepath=out_glb, export_format='GLB', use_selection=True, export_yup=True,
                                  export_apply=True, export_texcoords=False, export_normals=True,
                                  export_materials='NONE', export_colors=True, export_animations=False)
    rep['ok'] = os.path.exists(out_glb)
    rep['bytes'] = os.path.getsize(out_glb) if rep['ok'] else 0

if rdir and not rep['problems']:
    os.makedirs(rdir, exist_ok=True)
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sh = sc.display.shading
    sh.light, sh.color_type = 'STUDIO', 'VERTEX'
    sh.show_shadows = True
    sh.show_cavity = True
    sc.render.resolution_x, sc.render.resolution_y = 900, 600
    sc.render.film_transparent = False
    if sc.world is None:
        sc.world = bpy.data.worlds.new('w')
    sc.world.color = (0.55, 0.62, 0.68)
    # a ground plate so floating and contact read
    bpy.ops.mesh.primitive_plane_add(size=1)
    gp = bpy.context.object
    span = max(hi.x - lo.x, hi.y - lo.y, 10)
    gp.scale = (span * 1.6, span * 1.6, 1)
    gp.location = ((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, 0)
    gm = gp.data.color_attributes.new('Col', 'FLOAT_COLOR', 'CORNER')
    for d in gm.data:
        d.color = (0.20, 0.17, 0.11, 1)
    c = (lo + hi) / 2
    size = (hi - lo).length
    cam_d = bpy.data.cameras.new('cam')
    cam_d.lens = 35
    cam = bpy.data.objects.new('cam', cam_d)
    sc.collection.objects.link(cam)
    sc.camera = cam
    # two whole views, then a close-up on real geometry: from far off, gaps and sparseness are invisible
    vs = [v.co for o in objs for v in o.data.vertices]
    near = sorted(vs, key=lambda v: (v - c).length)[len(vs) // 2] if vs else c
    for i, (az, el, tgt, dist) in enumerate([(-35, 22, c, size * 1.05), (145, 35, c, size * 1.05),
                                             (-60, 14, near, max(14.0, size * 0.12))]):
        a, e = math.radians(az), math.radians(el)
        d = Vector((math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e))) * dist
        c0, c = c, tgt
        cam.location = c + d
        cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
        png = os.path.join(rdir, f'view{i}.png')
        sc.render.filepath = png
        bpy.ops.render.render(write_still=True)
        rep['renders'].append(png)
        c = c0
done()
