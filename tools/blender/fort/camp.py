# The men's camp in the first weeks, and the arms casks, shut and then broken open on 26 May 1607.
# Written by Claude, 2026-11-25. Barrels, staves and chests are baked CC0 Poly Haven props (tools/blender/props).
SAIL, SAIL_OLD, POLE, BARK, IRON, STONE, CHAR = '#d8cfb4', '#bdb39a', '#7d6a52', '#4e3b2a', '#3a3a3a', '#8a8478', '#2a2420'
WOOD, CUT = '#6b5236', '#c9a874'


def shelter(P, r, x, y, yaw, length, h=7.0, half=4.2):
    ca, sa = math.cos(yaw), math.sin(yaw)
    at = lambda u, v, z: Vector((x + u * ca - v * sa, y + u * sa + v * ca, z))
    # forked sticks at each end and the ridge pole across them
    for u in (-length / 2, length / 2):
        P.log(at(u, 0, -0.3), at(u, 0, h - 0.2), 0.16, 0.12, POLE, sides=5, twist=r.random())
        for s in (-1, 1):
            P.log(at(u, 0, h - 0.9), at(u + s * 0.15, s * 0.5, h + 0.35), 0.08, 0.05, POLE, sides=4, caps=False)
    P.log(at(-length / 2 - 0.8, 0, h), at(length / 2 + 0.8, 0, h - 0.15), 0.14, 0.12, POLE, sides=5)
    col = SAIL if r.random() < 0.5 else SAIL_OLD
    sag = r.uniform(0.25, 0.5)

    def sheet(uu, vv):
        u = (uu - 0.5) * length
        v = (vv - 0.5) * 2                    # -1 .. 1 across the ridge
        z = h * (1 - abs(v)) - sag * math.sin(math.pi * uu) * (1 - abs(v)) * 1.5 + 0.12
        return at(u, v * half * (0.92 + 0.08 * math.sin(uu * 7 + x)), max(0.15, z))
    P.surface(sheet, 6, 4, col)
    # a pegged edge each side
    for s in (-1, 1):
        for u in (-length / 2 + 0.5, 0, length / 2 - 0.5):
            P.log(at(u, s * half * 0.95, 0.0), at(u, s * (half * 0.95 + 0.25), 0.45), 0.05, 0.04, POLE, sides=4)


def matchlock(P, base, top):
    base, top = Vector(base), Vector(top)
    d = (top - base).normalized()
    stock_end = base + d * 1.6
    P.board(base, stock_end, 0.32, 0.16, WOOD, up=(d.y, -d.x, 0.0001) if abs(d.z) < 0.99 else (1, 0, 0))
    P.log(stock_end - d * 0.2, top, 0.06, 0.05, IRON, sides=5)


def build():
    r = rng(1607)
    shel = Part('camp_shelters')
    spots = [(-48, 20, 0.2), (-30, 30, -0.35), (-12, 24, 0.5), (8, 32, 0.1), (-40, -4, 1.3), (-20, 4, 1.65),
             (24, 18, -0.6), (-52, -22, 0.9)]
    for i, (x, y, yaw) in enumerate(spots):
        shelter(shel, rng(30 + i), x + r.uniform(-3, 3), y + r.uniform(-3, 3), yaw + r.uniform(-.15, .15),
                r.uniform(10, 14))

    fire = Part('camp_fire')
    fx, fy = 2, 6
    for k in range(8):
        a = k * math.pi / 4 + r.uniform(-.15, .15)
        rad = 2.4 + r.uniform(-.2, .2)
        fire.box((fx + math.cos(a) * rad, fy + math.sin(a) * rad, -0.1), (r.uniform(.7, 1.0), r.uniform(.6, .9),
                 r.uniform(.45, .7)), STONE if k % 3 else '#77716a', rot=a, taper=0.7)
    for k in range(4):
        a = k * math.pi / 2 + 0.4
        fire.log((fx + math.cos(a) * 1.6, fy + math.sin(a) * 1.6, 0.25), (fx - math.cos(a) * 0.3, fy - math.sin(a) * 0.3,
                 0.45), 0.22, 0.18, CHAR, sides=5, cap_col='#5a3a22')
    apex = Vector((fx, fy, 6.2))
    for k in range(3):
        a = k * 2 * math.pi / 3 + 0.3
        fire.log((fx + math.cos(a) * 3.2, fy + math.sin(a) * 3.2, -0.2), apex + Vector((0, 0, 0.5)), 0.12, 0.09, POLE,
                 sides=5)
    fire.log(apex, apex - Vector((0, 0, 2.6)), 0.03, 0.03, IRON, sides=4, caps=False)       # chain
    fire.log(apex - Vector((0, 0, 2.6)), apex - Vector((0, 0, 3.9)), 0.75, 0.55, IRON, sides=8)  # the pot
    fire.mound((fx, fy, 0), 1.4, 0.25, '#3b3029', sides=7, rings=2)                          # ash

    # the arms, packed in casks, by the storehouse ground
    cx, cy = 40, -25
    bar = [(cx - 3, cy - 1, 0), (cx - 0.4, cy - 1.8, 70), (cx + 2.2, cy - 0.6, 150), (cx - 2.0, cy + 1.6, 210),
           (cx + 0.6, cy + 1.2, 290), (cx + 3.4, cy + 2.2, 40)]
    shut = Part('camp_casks')
    for i, (x, y, yaw) in enumerate(bar):
        shut.prop('barrel' if i % 2 else 'barrel_b', (x, y, 0), yaw=yaw, scale=r.uniform(.95, 1.05))
    chests = [(cx + 6.5, cy - 0.5, 12), (cx + 6.2, cy + 2.6, -8)]
    for x, y, yaw in chests:
        shut.prop('chest', (x, y, 0), yaw=yaw)

    opn = Part('camp_casks_open')
    r2 = rng(526)
    for i, (x, y, yaw) in enumerate(bar):
        if i in (1, 4):          # knocked over in the rush
            opn.prop('barrel' if i % 2 else 'barrel_b', (x + 0.4, y, 1.25), yaw=yaw + 30, lean=90)
        elif i in (0, 3):        # head stove in: only staves left
            opn.prop('staves', (x, y, 0), yaw=yaw * 2, scale=0.55)
        else:
            opn.prop('barrel' if i % 2 else 'barrel_b', (x, y, 0), yaw=yaw)
    for x, y, yaw in chests:
        opn.prop('chest', (x, y, 0), yaw=yaw + r2.uniform(-25, 25))
    # matchlocks leaning against the standing casks, butts on the ground
    for k in range(8):
        x, y, _ = bar[[2, 5][k % 2]]
        a = k * 0.8 + r2.uniform(-.3, .3)
        foot = (x + math.cos(a) * 2.4, y + math.sin(a) * 2.4, 0.05)
        matchlock(opn, foot, (x + math.cos(a) * 0.9, y + math.sin(a) * 0.9, 3.0 + r2.uniform(-.3, .4)))
    # three pikes leaning together
    tip = Vector((cx - 7, cy + 4, 13.0))
    for k in range(3):
        a = k * 2.1 + 0.5
        foot = Vector((cx - 7 + math.cos(a) * 2.2, cy + 4 + math.sin(a) * 2.2, 0))
        opn.log(foot, tip + Vector((math.cos(a) * 0.2, math.sin(a) * 0.2, 0)), 0.1, 0.08, POLE, sides=5)
        d = (tip - foot).normalized()
        opn.log(tip, tip + d * 1.0, 0.1, 0.01, IRON, sides=4)
    occlude()
