# The only defence on 26 May 1607: "the boughs of trees cast together in the form of a half moon" (John Smith).
# A half circle, radius 110 ft, bulging toward +Y, open to the river at -Y, in four quarters (the work's progress).
# Written by Claude, 2026-11-25 (replaces the local model's sparse draft).
BARK, BARK2, CUT, LEAF, LEAF2, DEAD, DEAD2 = '#4e3b2a', '#5a4632', '#c9a874', '#4f6b34', '#3e5a2a', '#6e5a36', '#7a6440'
R0 = 110.0


def arc(t, off=0.0, z=0.0):
    """t from 0 (the x=-110 end) to 1 (x=+110); off moves outward from the centre."""
    a = math.pi * (1 - t)
    return Vector((math.cos(a) * (R0 + off), math.sin(a) * (R0 + off), z))


def blob(P, c, size, r, col, stretch=None):
    """An irregular leafy mass: a randomly squashed, tilted octahedron (not the kit's umbrella-shaped tuft)."""
    s = size / 2
    ax = [Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))]
    rot = (Matrix.Rotation(r.uniform(0, 6.28), 3, 'Z') @ Matrix.Rotation(r.uniform(-.7, .7), 3, 'X'))
    if stretch is not None:                            # long along the heap
        yaw = math.atan2(stretch.y, stretch.x)
        rot = Matrix.Rotation(yaw, 3, 'Z') @ Matrix.Rotation(r.uniform(-.25, .25), 3, 'X')
    k = [r.uniform(.8, 1.15) * (1.6 if stretch is not None else 1), r.uniform(.6, 1.0), r.uniform(.45, .75)]
    v = {}
    for i in range(3):
        for sg in (1, -1):
            v[(i, sg)] = Vector(c) + rot @ (ax[i] * sg * s * k[i] * r.uniform(.8, 1.2))
    dark = '#33441f' if col in (LEAF, LEAF2) else '#4f4128'
    for sx in (1, -1):
        for sy in (1, -1):
            for sz in (1, -1):
                a, b, t = v[(0, sx)], v[(1, sy)], v[(2, sz)]
                face = (a, b, t) if sx * sy * sz > 0 else (b, a, t)
                P.tri(*face, col if sz > 0 else dark)


def bough(P, r, base, d, length, leaf):
    d = d.normalized()
    tip = base + d * length
    P.log(base, tip, .22, .07, BARK2, sides=5, caps=False, twist=r.random())
    side = d.cross(Vector((0, 0, 1)))
    if side.length < .1:
        side = Vector((1, 0, 0))
    side.normalize()
    for f in (.45, .75):                               # two twigs off the limb
        p = base + d * length * f
        q = p + (side * r.choice((-1, 1)) * r.uniform(.8, 1.6) + d * .8 + Vector((0, 0, r.uniform(0, .8))))
        P.tri(p, q, p + d * .4 + Vector((0, 0, .1)), BARK2)
        blob(P, q, r.uniform(1.8, 2.6), r, leaf)
    blob(P, tip, r.uniform(2.4, 3.4), r, leaf)


def build():
    r = rng(1607)
    for q in range(4):
        P = Part(f'brush_fence_{q + 1}')
        t0, t1 = q / 4, (q + 1) / 4
        L = math.pi * R0 / 4                            # feet of arc in this quarter
        # long trunks lying along the arc, crossing each other
        for k in range(7):
            ta = t0 + (t1 - t0) * (k / 7 + r.uniform(-.03, .03))
            tb = min(1.0, ta + r.uniform(.035, .06))
            a = arc(max(0, ta), r.uniform(-1.5, 1.5), r.uniform(.5, 1.6))
            b = arc(tb, r.uniform(-1.5, 1.5), r.uniform(.4, 2.2))
            P.log(a, b, r.uniform(.5, .7), .3, BARK, sides=6, cap_col=CUT, twist=r.random())
        # the heap's core: dark dead leaves every 3 ft so nothing shows through
        n = int(L / 3)
        for k in range(n + 1):
            t = t0 + (t1 - t0) * k / n
            along = arc(min(1, t + .001)) - arc(max(0, t - .001))
            blob(P, arc(t, r.uniform(-.8, .8), r.uniform(1.4, 2.2)), r.uniform(4.0, 5.2), r,
                 DEAD if r.random() < .55 else DEAD2, stretch=along)
        # boughs every 2-3 ft, at three heights, pointing out and up at varied angles
        n = int(L / 2.2)
        for k in range(n):
            t = t0 + (t1 - t0) * (k + r.random()) / n
            layer = k % 3
            z = (.4, 1.6, 3.0)[layer] + r.uniform(-.3, .3)
            base = arc(t, r.uniform(-2.2, 2.2), z)
            outward = arc(t) - arc(t, -1)                  # unit-ish, away from the centre
            along = arc(min(1, t + .001)) - arc(max(0, t - .001))
            d = (outward * r.uniform(-1, 1) + along.normalized() * r.uniform(-1, 1) +
                 Vector((0, 0, (.15, .55, 1.0)[layer] * r.uniform(.6, 1.4))))
            leaf = DEAD if r.random() < .35 else (LEAF if r.random() < .6 else LEAF2)
            bough(P, r, base, d, r.uniform(4, 7), leaf)
    occlude(height=4.5)
