"""dehorn_deer.py - runs inside Blender: cut the antlers off the SkinTokens-rigged TRELLIS deer, keeping the skin
weights, so pose_quadruped.py can pose an antlerless deer (a buck in April-June 1607 would carry short velvet antlers,
not the hard rack TRELLIS made). Antler vertices = those weighted mostly to the antler bones (bone_9..bone_12 on the
2026-11-26 rig) above the skull top (z > ZCUT, 0.27), sparing the right ear (y > 0.07, z < 0.30).

    set OUTDIR=<dir>
    blender -b --factory-startup --python tools/blender/dehorn_deer.py -- 0.27 --export
    blender -b -P E:/VN-Tools/skintokens/pose_quadruped.py -- <dir>/rigged_doe.glb <dir>/poses standing grazing startled
    blender -b --factory-startup --python tools/blender/bake_glb.py -- <dir>/poses/<pose>.glb         assets/animals/deer_<pose>.glb <report> --tris 1500 --scale 5.6 --voxel 0.06 --node deer_<pose>         --largest --pale-top -0.2
ceiling: bone names and the cut height are this rig's; a new rig needs them read again (probe the bone bboxes).
"""
"""Delete antler vertices from the rest-pose rigged deer, keep the skin, render a check, export rigged GLB."""
import bpy, bmesh, sys, math
from mathutils import Vector
import os
OUT = os.environ['OUTDIR']
ZCUT = float(sys.argv[sys.argv.index('--')+1])
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
bpy.ops.import_scene.gltf(filepath=r'E:\VN-Tools\skintokens\test\deer\rigged.glb')
bpy.data.objects.remove(bpy.data.objects['Icosphere'])
o = bpy.data.objects['Mesh_0']
gi = {o.vertex_groups[n].index for n in ['bone_9','bone_10','bone_11','bone_12']}
bm = bmesh.new(); bm.from_mesh(o.data)
dl = bm.verts.layers.deform.active
kill = []
for v in bm.verts:
    w = v[dl]
    if not w: continue
    g = max(w.items(), key=lambda kv: kv[1])[0]
    if g in gi and v.co.z > ZCUT and not (v.co.y > 0.07 and v.co.z < 0.30):
        kill.append(v)
print('KILL', len(kill))
bmesh.ops.delete(bm, geom=kill, context='VERTS')
bm.to_mesh(o.data); bm.free()
sc = bpy.context.scene
sc.render.engine='BLENDER_WORKBENCH'; sh=sc.display.shading; sh.light='STUDIO'; sh.color_type='TEXTURE'
sc.render.resolution_x, sc.render.resolution_y = 700, 700
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera=cam
ctr = Vector((-0.30, 0.0, 0.25))
for i,(az,el) in enumerate([(-90,10),(200,25),(0,80)]):
    a,e = math.radians(az), math.radians(el)
    cam.location = ctr + Vector((math.cos(e)*math.cos(a), math.cos(e)*math.sin(a), math.sin(e)))*0.6
    cam.rotation_euler = (ctr-cam.location).to_track_quat('-Z','Y').to_euler()
    sc.render.filepath = OUT + f'/head_{ZCUT}_{i}.png'; bpy.ops.render.render(write_still=True)
if '--export' in sys.argv:
    bpy.ops.export_scene.gltf(filepath=OUT + '/rigged_doe.glb', export_format='GLB')
