# James Fort as finished 15 June 1607 (Percy): "triangle wise, having three bulwarks at every corner like a half
# moon, and four or five pieces of artillery mounted in them". River side 420 ft on y=0; the apex about (0, 222).
# Written by Claude, 2026-11-25.
OAK, OLD, GREY, CUT, EARTH, IRON, WOOD = '#9a7b52', '#7d6a52', '#8a7a62', '#c9a874', '#6b5638', '#3a3a3a', '#6b5236'
SW, SE, N = Vector((-210, 0, 0)), Vector((210, 0, 0)), Vector((0, 222, 0))
MID = (SW + SE + N) / 3
BR = 25.0                                    # bulwark radius
GATE = 5.0                                   # half the gate gap


def post(P, r, at, out):
    """One split timber set upright, flat face outward, its foot buried."""
    h = r.uniform(11.0, 11.8)
    lean = Vector((r.uniform(-1, 1), r.uniform(-1, 1), 0)) * math.tan(math.radians(2)) * h
    c = r.random()
    P.board(at + Vector((0, 0, -0.3)), at + Vector((0, 0, h)) + lean, r.uniform(1.0, 1.15), 0.5,
            OAK if c < .5 else (OLD if c < .85 else GREY), up=(out.x, out.y, 0))


def wall(P, r, a, b, skip=None):
    d = (b - a)
    L = d.length
    d.normalize()
    out = Vector((d.y, -d.x, 0))
    if out.dot((a + b) / 2 - MID) < 0:
        out = -out
    n = int(L / 1.15)
    for i in range(n + 1):
        p = a + d * (i * L / n)
        if skip and skip(p):
            continue
        post(P, r, p, out)
    # one rail along the inside at 8 ft
    inn = -out * 0.55
    if skip:
        segs, cur = [], None
        for i in range(n + 1):
            p = a + d * (i * L / n)
            if skip(p):
                if cur:
                    segs.append(cur)
                cur = None
            else:
                cur = (cur[0], p) if cur else (p, p)
        if cur:
            segs.append(cur)
    else:
        segs = [(a, b)]
    for s0, s1 in segs:
        P.log(s0 + inn + Vector((0, 0, 8)), s1 + inn + Vector((0, 0, 8)), .22, .2, OLD, sides=6, cap_col=CUT)


def gun(P, r, at, aim):
    """A saker on a truck carriage, on the bulwark's platform, its muzzle toward aim."""
    d = (aim - at)
    d.z = 0
    d.normalize()
    side = Vector((-d.y, d.x, 0))
    z = at.z
    yaw = math.atan2(d.y, d.x)
    P.box((at.x, at.y, z + .9), (5.0, 2.5, 1.2), WOOD, rot=yaw, taper=.9)
    for f in (-1.7, 1.7):
        for s in (-1, 1):
            c = at + d * f + side * s * 1.45
            P.log(c + Vector((0, 0, z + .75)) - side * s * .2, c + Vector((0, 0, z + .75)) + side * s * .25, .75, .75,
                  WOOD, sides=8, cap_col='#4a3a26')
    br = at + Vector((0, 0, z + 2.5)) - d * 2.6
    P.log(br, br + d * 8 + Vector((0, 0, .25)), .45, .33, IRON, sides=8, cap_col='#1e1e1e')
    P.log(br, br - d * .7, .3, .15, IRON, sides=6)                 # the cascabel


def bulwark(P, r, c):
    toward = (MID - c)
    toward.z = 0
    toward.normalize()
    n = int(2 * math.pi * BR / 1.15)
    for i in range(n):
        a = 2 * math.pi * i / n
        rad = Vector((math.cos(a), math.sin(a), 0))
        if rad.dot(toward) > math.cos(math.radians(62)):            # leave the inside open
            continue
        post(P, r, c + rad * BR, rad)
    P.mound(c, 20, 4.0, EARTH, sides=12, rings=3)
    gun(P, r, c + Vector((0, 0, 3.6)) - toward * 9, c - toward * 60)


def build():
    r = rng(1607)
    corners = {'sw': SW, 'se': SE, 'n': N}
    for k, c in corners.items():
        bulwark(Part('bulwark_' + k), r, c)

    def between(a, b):
        d = (b - a).normalized()
        return a + d * (BR - 1), b - d * (BR - 1)
    a, b = between(SW, SE)
    wall(Part('palisade_river'), r, a, b, skip=lambda p: abs(p.x) < GATE + .4)
    wall(Part('palisade_east'), r, *between(SE, N))
    wall(Part('palisade_west'), r, *between(N, SW))

    G = Part('gate')
    for s in (-1, 1):
        G.log((s * (GATE + .2), 0, -.5), (s * (GATE + .2), 0, 13.2), .75, .7, OLD, sides=8, cap_col=CUT)
        # a leaf of planks on a frame, standing open inward (+Y)
        hinge = Vector((s * GATE, .4, 0))
        d = Vector((-s * math.cos(math.radians(70)), math.sin(math.radians(70)), 0))
        for k in range(4):
            p = hinge + d * (k * 1.2 + .6)
            G.board(p + Vector((0, 0, .2)), p + Vector((0, 0, 10.5)), 1.2, .35, OAK if k % 2 else OLD,
                    up=(-d.y, d.x, 0))
        for z in (2.0, 8.5):
            G.board(hinge + Vector((0, 0, z)) + Vector((-d.y, d.x, 0)) * .35, hinge + d * 4.8 + Vector((0, 0, z)) +
                    Vector((-d.y, d.x, 0)) * .35, .6, .3, OLD, up=(-d.y, d.x, 0))
    G.log((-(GATE + .6), 0, 12.6), ((GATE + .6), 0, 12.6), .5, .5, OLD, sides=6, cap_col=CUT)   # lintel
    occlude(height=8)
