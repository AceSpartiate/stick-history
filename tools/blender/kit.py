"""kit.py - the modelling helpers a local model calls to build Stick History's Blender assets.

Runs INSIDE Blender (asset_job.py loads it before the model's script). Units: 1 = one foot,
Blender Z up, ground at z=0; the glTF export turns it Y-up for three.js. Colours are written
as sRGB hex and converted to linear here, once (glTF COLOR_0 is linear; the game's RGB()
hands the renderer linear too). Each Part becomes one named object = one toggle group in
the game. The game's style: low-poly WITH FORM - round timber is an 8-sided prism that
tapers, nothing is a grid of identical copies, occlusion is baked into vertex colour.
2026-11-09.
"""
import math, random
import bpy, bmesh
from mathutils import Vector, Matrix

PARTS = []


def lin(hexs):
    """'#b08a5a' -> linear RGB tuple."""
    h = hexs.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def rng(seed):
    """A seeded random.Random: use it for every variation so the asset rebuilds identically."""
    return random.Random(seed)


def _v(p):
    return Vector(p) if not isinstance(p, Vector) else p.copy()


def _frame(a, b):
    """Two unit vectors perpendicular to a->b."""
    ax = (b - a).normalized()
    ref = Vector((0, 0, 1)) if abs(ax.z) < 0.9 else Vector((1, 0, 0))
    u = ax.cross(ref).normalized()
    return u, ax.cross(u).normalized()


class Part:
    """One named object (a toggle group in the game). Build it with the methods below."""

    def __init__(self, name):
        self.name, self.verts, self.faces, self.cols = name, [], [], []
        PARTS.append(self)

    def _face(self, pts, col):
        i = len(self.verts)
        self.verts.extend(_v(p) for p in pts)
        self.faces.append(tuple(range(i, i + len(pts))))
        self.cols.append([lin(col) if isinstance(col, str) else col] * len(pts) if not isinstance(col, list) else
                         [lin(c) if isinstance(c, str) else c for c in col])

    def quad(self, a, b, c, d, col):
        """A four-sided face a,b,c,d counter-clockwise seen from its front. col: hex or list of 4 hexes."""
        self._face([a, b, c, d], col)

    def tri(self, a, b, c, col):
        """A triangle, counter-clockwise seen from its front."""
        self._face([a, b, c], col)

    def prop(self, name, at, yaw=0.0, scale=1.0, lean=0.0):
        """Place a ready-made prop from the library (see PROPS) into this Part: at=(x,y,z) of its base centre,
        yaw in degrees about the vertical, lean in degrees (tips it over toward +x before the yaw; 90 = lying on its
        side). The prop keeps its own colours. Vary yaw/scale between copies so no two look identical."""
        verts, faces, cols = _load_prop(name)
        m = (Matrix.Translation(_v(at)) @ Matrix.Rotation(math.radians(yaw), 4, 'Z') @
             Matrix.Rotation(math.radians(lean), 4, 'Y') @ Matrix.Scale(scale, 4))
        i = len(self.verts)
        self.verts.extend(m @ v for v in verts)
        self.faces.extend(tuple(i + k for k in f) for f in faces)
        self.cols.extend(cols)

    def log(self, a, b, r0, r1=None, col='#7d6a52', col1=None, sides=8, caps=True, cap_col=None, twist=0.0):
        """Round timber from point a to point b: an N-sided prism, radius r0 at a tapering to r1 at b.
        For posts, trunks, logs, poles, barrels' staves, gun barrels. cap_col colours the end faces
        (cut wood is lighter: '#c9a874'). twist rotates the facets (radians) so neighbours differ."""
        a, b = _v(a), _v(b)
        r1 = r0 if r1 is None else r1
        u, w = _frame(a, b)
        ring = lambda c, r: [c + (u * math.cos(twist + 2 * math.pi * k / sides) +
                                  w * math.sin(twist + 2 * math.pi * k / sides)) * r for k in range(sides)]
        A, B = ring(a, r0), ring(b, r1)
        for k in range(sides):
            n = (k + 1) % sides
            self.quad(A[k], A[n], B[n], B[k], [col, col, col1 or col, col1 or col])
        if caps:
            cc = cap_col or col
            self._face(list(reversed(A)), cc)
            self._face(B, cc)

    def board(self, a, b, width, thick, col='#b08a5a', up=(0, 0, 1)):
        """A flat rectangular timber (plank, split post, rail, clapboard) from a to b. 'up' is the
        direction its WIDTH faces across (default: lying flat; pass a horizontal vector for an
        upright wall board facing that way)."""
        a, b = _v(a), _v(b)
        ax = (b - a).normalized()
        upv = Vector(up)
        side = ax.cross(upv)
        if side.length < 1e-6:
            side = ax.cross(Vector((1, 0, 0)))
        side.normalize()
        nrm = side.cross(ax).normalized()
        hw, ht = side * width / 2, nrm * thick / 2
        c = [a - hw - ht, a + hw - ht, a + hw + ht, a - hw + ht]
        d = [p + (b - a) for p in c]
        for k in range(4):
            n = (k + 1) % 4
            self.quad(c[k], c[n], d[n], d[k], col)
        self._face(list(reversed(c)), col)
        self._face(d, col)

    def box(self, center, size, col='#7d6a52', rot=0.0, taper=1.0):
        """An axis box (sx,sy,sz) standing on center's z (center is the BOTTOM middle), turned rot
        radians about Z. taper < 1 shrinks the top. Use for chests, carriages, stones - not round things."""
        cx, cy, cz = center
        sx, sy, sz = size
        cs, sn = math.cos(rot), math.sin(rot)
        P = lambda x, y, z: Vector((cx + x * cs - y * sn, cy + x * sn + y * cs, cz + z))
        bot = [P(-sx / 2, -sy / 2, 0), P(sx / 2, -sy / 2, 0), P(sx / 2, sy / 2, 0), P(-sx / 2, sy / 2, 0)]
        t = taper
        top = [P(-sx * t / 2, -sy * t / 2, sz), P(sx * t / 2, -sy * t / 2, sz), P(sx * t / 2, sy * t / 2, sz),
               P(-sx * t / 2, sy * t / 2, sz)]
        for k in range(4):
            n = (k + 1) % 4
            self.quad(bot[k], bot[n], top[n], top[k], col)
        self._face(list(reversed(bot)), col)
        self._face(top, col)

    def mound(self, center, radius, height, col='#5a4630', sides=8, rings=3):
        """A low dome of earth or a pile (corn hill, earthwork, heap), base at center's z."""
        c = _v(center)
        prev = [c + Vector((math.cos(2 * math.pi * k / sides) * radius, math.sin(2 * math.pi * k / sides) * radius,
                            0)) for k in range(sides)]
        for r in range(1, rings + 1):
            f = r / rings
            rad, z = radius * math.cos(f * math.pi / 2), height * math.sin(f * math.pi / 2)
            if r == rings:
                top = c + Vector((0, 0, height))
                for k in range(sides):
                    self.tri(prev[k], prev[(k + 1) % sides], top, col)
            else:
                cur = [c + Vector((math.cos(2 * math.pi * k / sides) * rad, math.sin(2 * math.pi * k / sides) * rad,
                                   z)) for k in range(sides)]
                for k in range(sides):
                    n = (k + 1) % sides
                    self.quad(prev[k], prev[n], cur[n], cur[k], col)
                prev = cur

    def surface(self, fn, nu, nv, col='#d8cfb4', both=True):
        """A curved sheet (sail, awning, cloth, thatch skin): fn(u,v) -> (x,y,z) for u,v in 0..1,
        nu x nv cells. both=True adds the back face so it shows from either side."""
        g = [[_v(fn(i / nu, j / nv)) for j in range(nv + 1)] for i in range(nu + 1)]
        for i in range(nu):
            for j in range(nv):
                a, b, c, d = g[i][j], g[i + 1][j], g[i + 1][j + 1], g[i][j + 1]
                self.quad(a, b, c, d, col)
                if both:
                    self.quad(a, d, c, b, col)

    def branch_spray(self, base, direction, length, r, rnd, col='#4e3b2a', leaf='#4f6b34', forks=3, depth=2):
        """A forked cut bough: a tapering limb with forks and leafy tufts (small low mounds of leaf
        colour at the tips). For brush fences, felled crowns, piled boughs. rnd = rng(seed)."""
        base, d = _v(base), Vector(direction).normalized()
        tip = base + d * length
        self.log(base, tip, r, r * 0.35, col, sides=5, caps=False, twist=rnd.random())
        if depth <= 0:
            self.tuft(tip, max(length * 0.9, 1.4), rnd, leaf)
            return
        for _ in range(forks):
            nd = (d + Vector((rnd.uniform(-.7, .7), rnd.uniform(-.7, .7), rnd.uniform(-.2, .5)))).normalized()
            start = base + d * length * rnd.uniform(.45, .9)
            self.branch_spray(start, nd, length * rnd.uniform(.4, .6), r * .45, rnd, col, leaf, max(2, forks - 1),
                              depth - 1)

    def tuft(self, center, size, rnd, leaf='#4f6b34'):
        """A clump of leaves: an irregular 6-sided double cone, size across."""
        c = _v(center)
        s = size / 2
        top, bot = c + Vector((0, 0, s * .7)), c - Vector((0, 0, s * .45))
        ring = [c + Vector((math.cos(k * math.pi / 3 + rnd.random() * .4) * s * rnd.uniform(.75, 1.1),
                            math.sin(k * math.pi / 3 + rnd.random() * .4) * s * rnd.uniform(.75, 1.1),
                            rnd.uniform(-.15, .15) * s)) for k in range(6)]
        shade = [leaf, '#3e5a2a', leaf]
        for k in range(6):
            n = (k + 1) % 6
            self.tri(ring[k], ring[n], top, leaf)
            self.tri(ring[n], ring[k], bot, shade[k % 3])


def occlude(ground=0.55, height=5.0, under=0.72):
    """Bake occlusion into every Part's colours: darker near the ground (factor 'ground' at z=0,
    full colour by 'height' feet) and on downward-facing faces ('under'). Call once at the end of build()."""
    for p in PARTS:
        for fi, f in enumerate(p.faces):
            pts = [p.verts[i] for i in f]
            n = (pts[1] - pts[0]).cross(pts[2] - pts[0])
            down = under if (n.length > 0 and n.normalized().z < -0.3) else 1.0
            for k, i in enumerate(f):
                z = max(0.0, p.verts[i].z)
                g = ground + (1 - ground) * min(1.0, z / height)
                c = p.cols[fi][k]
                p.cols[fi][k] = tuple(x * g * down for x in c)


import os as _os
PROP_DIR = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'props')   # tools/blender/props
_PROPS = {}


def _load_prop(name):
    """Read props/<name>.glb (made by bake_glb.py) as verts, faces and per-corner linear colours. The imported
    objects are removed again at once, so only Parts reach the export."""
    if name in _PROPS:
        return _PROPS[name]
    path = _os.path.join(PROP_DIR, name + '.glb')
    if not _os.path.exists(path):
        raise ValueError(f'no prop named "{name}"; the library has: '
                         + ', '.join(sorted(f[:-4] for f in _os.listdir(PROP_DIR) if f.endswith('.glb'))))
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    verts, faces, cols = [], [], []
    for ob in [o for o in bpy.data.objects if o not in before]:
        if ob.type == 'MESH':
            me = ob.data
            mw = ob.matrix_world
            i = len(verts)
            verts.extend(mw @ v.co for v in me.vertices)
            ca = me.color_attributes.active_color or (me.color_attributes[0] if me.color_attributes else None)
            for p in me.polygons:
                faces.append(tuple(i + v for v in p.vertices))
                if ca is not None and ca.domain == 'CORNER':
                    cols.append([tuple(ca.data[li].color)[:3] for li in p.loop_indices])
                elif ca is not None:
                    cols.append([tuple(ca.data[v].color)[:3] for v in p.vertices])
                else:
                    cols.append([(0.4, 0.3, 0.2)] * len(p.vertices))
        bpy.data.objects.remove(ob)
    _PROPS[name] = (verts, faces, cols)
    return _PROPS[name]


def realize():
    """Turn every Part into a Blender object with a linear colour attribute. Called by the harness."""
    objs = []
    for p in PARTS:
        me = bpy.data.meshes.new(p.name)
        me.from_pydata([tuple(v) for v in p.verts], [], p.faces)
        attr = me.color_attributes.new('Col', 'FLOAT_COLOR', 'CORNER')
        k = 0
        for fi, poly in enumerate(me.polygons):
            for j, li in enumerate(poly.loop_indices):
                c = p.cols[fi][j]
                attr.data[li].color = (c[0], c[1], c[2], 1.0)
        me.color_attributes.active_color = attr
        me.validate()
        ob = bpy.data.objects.new(p.name, me)
        bpy.context.scene.collection.objects.link(ob)
        objs.append(ob)
    return objs
