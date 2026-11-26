"""bake_glb.py - runs inside Blender: turn a textured model (TRELLIS.2 output, a CC0 Poly Haven glTF) into a game
asset in this game's own look: few triangles, colour baked into the vertices, no textures.

    blender -b --factory-startup --python tools/blender/bake_glb.py -- <in.glb|gltf> <out.glb> <report.json> \
        --tris N [--height FT | --scale S] [--voxel FT] [--node name] [--keep a,b] [--yaw DEG] [--render <dir>]

Why: TRELLIS.2 writes 58-65 MB GLBs with PBR texture maps, and a Poly Haven model comes with 2k maps. A Chromebook
loads neither well, and texture-mapped realism would sit wrongly beside this game's vertex-coloured, low-poly world.
So: optionally fuse it into one closed shell (--voxel, the voxel size in feet: separate staves or a scan's loose
skin will not decimate cleanly otherwise), decimate to the budget, then give each corner the colour of the nearest
point on the ORIGINAL surface, read from its base-colour map shrunk to 128 px (a neighbourhood, not one noisy texel),
and drop the maps. The result reads like everything
else in the game and costs a few hundred KB.

--height scales the model so it stands that many feet tall (TRELLIS has no real units); --keep keeps only the named
source objects (one barrel out of a group); --yaw turns it about the vertical. The output sits on z=0, centred on x,y.
Report: {"ok","problems","tris","bytes","bbox","renders"}. ceiling: base colour only (no AO baked in); one node out.
"""
import json, math, os, sys
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix, geometry
from mathutils.bvhtree import BVHTree

argv = sys.argv[sys.argv.index('--') + 1:]
src, out_glb, report = argv[0], argv[1], argv[2]
opt = lambda k, d=None: argv[argv.index(k) + 1] if k in argv else d
TRIS = int(opt('--tris', 3000))
rep = {'ok': False, 'problems': [], 'tris': 0, 'bytes': 0, 'bbox': None, 'renders': []}


def done():
    json.dump(rep, open(report, 'w'), indent=1)
    sys.exit(0)


for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)
bpy.ops.import_scene.gltf(filepath=os.path.abspath(src))
keep = [k for k in (opt('--keep') or '').split(',') if k]
meshes = [o for o in bpy.data.objects if o.type == 'MESH' and (not keep or any(k in o.name for k in keep))]
if not meshes:
    rep['problems'].append('no mesh objects' + (f' matching {keep}' if keep else ''))
    done()
for o in list(bpy.data.objects):
    if o not in meshes:
        bpy.data.objects.remove(o)

# bake parent transforms into the meshes, then join into one
for o in meshes:
    mw = o.matrix_world.copy()
    o.parent = None
    o.data.transform(mw)
    o.matrix_world = Matrix.Identity(4)
bpy.ops.object.select_all(action='DESELECT')
for o in meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
if len(meshes) > 1:
    bpy.ops.object.join()
ob = bpy.context.view_layer.objects.active
me = ob.data


def base_image(mat):
    """The image feeding Base Color, else None (then the material's flat base colour is used)."""
    if not mat or not mat.use_nodes:
        return None
    for n in mat.node_tree.nodes:
        if n.type == 'BSDF_PRINCIPLED':
            inp = n.inputs['Base Color']
            seen, stack = set(), [l.from_node for l in inp.links]
            while stack:
                m = stack.pop()
                if m in seen:
                    continue
                seen.add(m)
                if m.type == 'TEX_IMAGE' and m.image:
                    return m.image
                stack += [l.from_node for i in m.inputs for l in i.links]
    return None


def flat_colour(mat):
    if mat and mat.use_nodes:
        for n in mat.node_tree.nodes:
            if n.type == 'BSDF_PRINCIPLED':
                return tuple(n.inputs['Base Color'].default_value)[:3]
    return (0.5, 0.5, 0.5)


S = 128
maps = []
for mat in me.materials:
    img = base_image(mat)
    if img is None:
        maps.append(('flat', flat_colour(mat)))
        continue
    small = img.copy()
    small.scale(S, S)
    px = np.array(small.pixels[:], dtype=np.float32).reshape(S, S, 4)[..., :3]
    if small.colorspace_settings.name.lower().startswith('srgb'):
        px = np.where(px <= 0.04045, px / 12.92, ((px + 0.055) / 1.055) ** 2.4)   # to linear, as kit.lin() does
    maps.append(('img', px))
    bpy.data.images.remove(small)

# units first (glTF import is already Z-up): scale, turn, stand on z=0, centre - so --voxel is in feet
vs = np.array([v.co[:] for v in me.vertices])
lo, hi = vs.min(0), vs.max(0)
s = float(opt('--scale', 1.0))
if opt('--height'):
    s = float(opt('--height')) / max(hi[2] - lo[2], 1e-6)
yaw = math.radians(float(opt('--yaw', 0)))
c = (lo + hi) / 2
me.transform(Matrix.Translation(Vector((-c[0], -c[1], -lo[2]))))
me.transform(Matrix.Rotation(yaw, 4, 'Z') @ Matrix.Scale(s, 4))
me.update()

# the colour source: a triangulated copy of the full-detail mesh, with its UVs, in a BVH tree
src_bm = bmesh.new()
src_bm.from_mesh(me)
bmesh.ops.triangulate(src_bm, faces=src_bm.faces[:])
src_bm.faces.ensure_lookup_table()
src_uv = src_bm.loops.layers.uv.active
tree = BVHTree.FromBMesh(src_bm)


def colour_at(pt):
    loc, _n, fi, _d = tree.find_nearest(pt)
    f = src_bm.faces[fi]
    kind, m = maps[f.material_index] if maps and f.material_index < len(maps) else ('flat', (0.5, 0.5, 0.5))
    if kind == 'flat' or src_uv is None:
        return m if kind == 'flat' else (0.5, 0.5, 0.5)
    a, b, cc = (l.vert.co for l in f.loops)
    ua, ub, uc = (Vector((l[src_uv].uv.x, l[src_uv].uv.y, 0)) for l in f.loops)
    uv = geometry.barycentric_transform(loc, a, b, cc, ua, ub, uc)
    x = int((uv.x % 1.0) * (S - 1) + 0.5)
    y = int((uv.y % 1.0) * (S - 1) + 0.5)
    return m[y, x]


# --voxel V: fuse into one closed shell first (staves, scans and TRELLIS skins decimate cleanly only then)
if opt('--voxel'):
    rm = ob.modifiers.new('rm', 'REMESH')
    rm.mode, rm.voxel_size = 'VOXEL', float(opt('--voxel'))
    bpy.ops.object.modifier_apply(modifier='rm')
t0 = sum(len(p.vertices) - 2 for p in ob.data.polygons)
if t0 > TRIS:
    md = ob.modifiers.new('dec', 'DECIMATE')
    md.ratio = TRIS / t0
    md.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier='dec')
me = ob.data

col = me.color_attributes.new('Col', 'FLOAT_COLOR', 'CORNER')
for p in me.polygons:
    ctr = p.center
    for li, vi in zip(p.loop_indices, p.vertices):
        cl = colour_at(me.vertices[vi].co * 0.65 + ctr * 0.35)   # pulled in from the corner: no bleed across edges
        col.data[li].color = (float(cl[0]), float(cl[1]), float(cl[2]), 1.0)
me.color_attributes.active_color = col
for layer in list(me.uv_layers):
    me.uv_layers.remove(layer)
me.materials.clear()
ob.name = me.name = opt('--node', 'model')
me.update()
src_bm.free()

vs = np.array([v.co[:] for v in me.vertices])
lo, hi = Vector(vs.min(0)), Vector(vs.max(0))
rep['bbox'] = [list(lo), list(hi)]
rep['tris'] = sum(len(p.vertices) - 2 for p in me.polygons)
os.makedirs(os.path.dirname(os.path.abspath(out_glb)), exist_ok=True)
bpy.ops.object.select_all(action='DESELECT')
ob.select_set(True)
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

rdir = opt('--render')
if rdir:
    os.makedirs(rdir, exist_ok=True)
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sh = sc.display.shading
    sh.light, sh.color_type, sh.show_shadows, sh.show_cavity = 'STUDIO', 'VERTEX', True, True
    sc.render.resolution_x, sc.render.resolution_y = 900, 600
    if sc.world is None:
        sc.world = bpy.data.worlds.new('w')
    sc.world.color = (0.55, 0.62, 0.68)
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    cam.data.lens = 35
    sc.collection.objects.link(cam)
    sc.camera = cam
    ctr, size = (lo + hi) / 2, (hi - lo).length
    for i, (az, el) in enumerate([(-35, 22), (145, 35)]):
        a, e = math.radians(az), math.radians(el)
        cam.location = ctr + Vector((math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e))) * size * 1.1
        cam.rotation_euler = (ctr - cam.location).to_track_quat('-Z', 'Y').to_euler()
        png = os.path.join(rdir, f'bake{i}.png')
        sc.render.filepath = png
        bpy.ops.render.render(write_still=True)
        rep['renders'].append(png)
done()
