# A Powhatan house (yehakin), from John Smith's description: "built like our arbors of small young springs bowed and
# tied, and so close covered with mats or the barks of trees very handsomely ... at the top of the house there is a
# hole made for the smoke". 24 x 12 x 10 ft; the game scales it per house. Written by Claude, 2026-11-25.
# The shell is a long dome on a stadium plan: straight sides, round ends, every vertical section a quarter ellipse,
# so the ends round over like a loaf's instead of coming to a point.
L, W, H = 24.0, 12.0, 10.0
A = L / 2 - W / 2            # half-length of the straight middle (the ends are half circles in plan)
BARK = ['#6b5a44', '#7a6650', '#5e4e3a', '#83705a']
MAT = ['#b8a47a', '#a8946a', '#c2ae84']
POLE, DARK = '#8a7454', '#2a2018'
PER = [2 * A, math.pi * W / 2, 2 * A, math.pi * W / 2]       # perimeter pieces: side, +x end, side, -x end
TOT = sum(PER)


def plan(t):
    """t 0..1 round the plan at the ground: (x, y, outward normal x, y)."""
    d = t * TOT
    if d < PER[0]:
        return -A + d, -W / 2, 0, -1
    d -= PER[0]
    if d < PER[1]:
        a = -math.pi / 2 + d / (W / 2)
        return A + math.cos(a) * W / 2, math.sin(a) * W / 2, math.cos(a), math.sin(a)
    d -= PER[1]
    if d < PER[2]:
        return A - d, W / 2, 0, 1
    d -= PER[2]
    a = math.pi / 2 + d / (W / 2)
    return -A + math.cos(a) * W / 2, math.sin(a) * W / 2, math.cos(a), math.sin(a)


def at(t, h, grow=0.0):
    """h 0 (ground) .. 1 (ridge): the contour draws in toward the ridge line as a quarter ellipse."""
    x, y, nx, ny = plan(t)
    rho = math.cos(h * math.pi / 2)                  # 1 at the ground, 0 at the ridge
    cx = max(-A, min(A, x))                          # the nearest point of the ridge line
    return Vector((cx + (x - cx) * rho + nx * grow, y * rho + ny * grow, H * math.sin(h * math.pi / 2) + grow))


def end_angle(t):
    """For a point on the +x end: its angle off the house's axis (radians), else None."""
    x, y, nx, ny = plan(t)
    return math.atan2(ny, nx) if x > A + 1e-6 else None


def build():
    r = rng(1607)
    P = Part('yehakin')
    rows = 6
    for row in range(rows):
        h0, h1 = row / rows, min(1.0, (row + 1.3) / rows)
        grow = .04 * (rows - row)
        cols = MAT if row < 2 else BARK
        cuts, t = [0.0], 0.0
        while t < 1.0:
            t = min(1.0, t + r.uniform(.025, .045))
            cuts.append(t)
        for t0, t1 in zip(cuts, cuts[1:]):
            tm = (t0 + t1) / 2
            x, y, _, _ = plan(tm)
            if row == rows - 1 and abs(x) < 3.0:
                continue                                  # the smoke hole
            ea = end_angle(tm)
            if ea is not None and abs(ea) < .5 and row < 3:
                continue                                  # the doorway, low in the +x end
            col = cols[r.randrange(len(cols))]

            def f(u, v, t0=t0, t1=t1, h0=h0, h1=h1, grow=grow):
                return at(t0 + (t1 - t0) * u, h0 + (h1 - h0) * v, grow)
            P.surface(f, 1, 2, col, both=True)
    # the doorway: a dark opening, a bent sapling framing it, a mat hung half across
    hd = 3 / rows
    xd = A + (W / 2) * math.cos(hd * math.pi / 2) * math.cos(.5)
    zd = H * math.sin(hd * math.pi / 2)
    arch = [Vector((xd + .4, -2.5 * math.cos(a), zd * math.sin(a) + .1)) for a in [i * math.pi / 8 for i in range(9)]]
    for a, b in zip(arch, arch[1:]):
        P.log(a, b, .14, .14, POLE, sides=4, caps=False)
    for sg in (1, -1):
        q = [(xd - .6, -2.4 * sg, .02), (xd - .6, 2.4 * sg, .02), (xd - .6, 2.4 * sg, zd), (xd - .6, -2.4 * sg, zd)]
        P.quad(*q, DARK)
    hang = [(xd + .5, -2.5, zd), (xd + .5, .1, zd), (xd + .7, .3, 1.0), (xd + .7, -2.3, .8)]
    P.quad(*hang, MAT[0])
    P.quad(hang[0], hang[3], hang[2], hang[1], MAT[1])
    # ribs over the smoke hole
    for x in (-2.6, 0, 2.6):
        pts = [Vector((x, (W / 2) * math.cos(h * math.pi / 2) * s, H * math.sin(h * math.pi / 2) + .35))
               for s, h in ((-1, .7), (-1, .85), (1, 1.0), (1, .85), (1, .7))]
        for a, b in zip(pts, pts[1:]):
            P.log(a, b, .12, .12, POLE, sides=4, caps=False)
    occlude(ground=.6, height=6)
