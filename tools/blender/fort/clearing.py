# Forest being cleared, in three stages that add to each other: felled trunks, stumps, clapboard stacks, a sawpit.
# Clapboard was the Company's first return cargo. Written by Claude, 2026-11-25.
BARK, BARK2, CUT, OAK, OLD, LEAF, DEAD, EARTH = '#4e3b2a', '#5a4632', '#c9a874', '#b08a5a', '#9a7b52', '#4f6b34', '#6e5a36', '#5a4630'


def stump(P, r, x, y):
    rad, h = r.uniform(1.0, 1.5), r.uniform(1.5, 2.5)
    P.log((x, y, -0.3), (x, y, h), rad * 1.08, rad, BARK, sides=8, cap_col=CUT, twist=r.random())
    for k in range(r.randint(3, 4)):                      # roots
        b = r.random() * 6.28
        P.log((x + math.cos(b) * rad * .6, y + math.sin(b) * rad * .6, .7),
              (x + math.cos(b) * (rad + 2.2), y + math.sin(b) * (rad + 2.2), -.25), .5, .18, BARK2, sides=5, caps=False)
    for k in range(3):                                    # chips
        b, d = r.random() * 6.28, r.uniform(rad + .5, rad + 3)
        P.box((x + math.cos(b) * d, y + math.sin(b) * d, 0), (.5, .3, .08), CUT, rot=r.random() * 3)


def trunk(P, r, x, y, yaw):
    L, rad = r.uniform(30, 50), r.uniform(1.0, 1.4)
    d = Vector((math.cos(yaw), math.sin(yaw), 0))
    a, b = Vector((x, y, rad * .9)) - d * L / 2, Vector((x, y, rad * .55)) + d * L / 2
    P.log(a, b, rad, rad * .45, BARK, sides=8, cap_col=CUT, twist=r.random())
    side = Vector((-d.y, d.x, 0))
    for k in range(r.randint(3, 5)):                      # lopped limbs, stubs pointing up and out
        t = r.uniform(.45, .95)
        p = a + (b - a) * t
        s = side * r.choice((-1, 1))
        P.log(p, p + (s * r.uniform(1, 2.5) + Vector((0, 0, r.uniform(.8, 2)))), rad * .3, rad * .2, BARK2, sides=5,
              cap_col=CUT)
    # the top's brush, left lying where it fell
    tip = b + d * 2
    for k in range(3):
        P.branch_spray(tip + side * r.uniform(-2, 2), d + side * r.uniform(-.8, .8) + Vector((0, 0, .3)),
                       r.uniform(6, 9), .3, r, BARK2, DEAD if r.random() < .5 else LEAF, forks=2, depth=1)


def stack(P, r, x, y, yaw):
    ca, sa = math.cos(yaw), math.sin(yaw)
    at = lambda u, v, z: (x + u * ca - v * sa, y + u * sa + v * ca, z)
    for v in (-1.6, 1.6):                                  # two skids
        P.log(at(-3.2, v, .3), at(3.2, v, .3), .3, .28, BARK2, sides=6, cap_col=CUT)
    layers = r.randint(5, 8)
    for i in range(layers):
        z = .62 + i * .17
        for k in range(6):
            u = -2.6 + k * 1.04 + r.uniform(-.05, .05)
            P.board(at(u, -2.5, z), at(u + r.uniform(-.1, .1), 2.5, z), .85, .15, OAK if r.random() < .7 else OLD)


def sawpit(P, r, x, y):
    for (a, b) in (((-6, -2), (6, -2)), ((-6, 2), (6, 2)), ((-6, -2), (-6, 2)), ((6, -2), (6, 2))):
        P.log((x + a[0], y + a[1], .4), (x + b[0], y + b[1], .4), .45, .42, BARK2, sides=6, cap_col=CUT)
    P.quad((x - 5.6, y - 1.6, .05), (x + 5.6, y - 1.6, .05), (x + 5.6, y + 1.6, .05), (x - 5.6, y + 1.6, .05),
           '#2e2418')                                        # the pit's dark mouth
    P.log((x - 7.5, y, 1.2), (x + 7.5, y, 1.2), .9, .8, BARK, sides=8, cap_col=CUT)   # a log across, being sawn
    P.board((x + 1.5, y, 2.1), (x + 1.5, y, -2.5), .5, .06, '#8a8a88', up=(1, 0, 0))    # the pit saw


def build():
    r = rng(1607)
    stages = {
        'clearing_1': dict(trunks=[(-50, 30, .3), (-20, 50, 2.6), (35, 45, 1.1), (60, 20, -.4)],
                           stumps=[(-60, 55), (-40, 15), (-10, 35), (20, 60), (45, 30), (70, 50)],
                           stacks=[(-30, -10, .2)]),
        'clearing_2': dict(trunks=[(-70, -20, 1.9), (-5, 5, .9), (40, -5, 2.4), (80, -25, .1)],
                           stumps=[(-85, 0), (-60, -40), (-25, -30), (10, -20), (30, 15), (60, -45), (85, 5)],
                           stacks=[(0, -50, 1.4), (55, -60, .5)]),
        'clearing_3': dict(trunks=[(-80, 40, -.6), (15, -60, .2), (80, 55, 1.6)],
                           stumps=[(-90, -55), (-50, -65), (-15, 65), (5, -40), (40, 65), (75, -10), (90, 35)],
                           stacks=[(-55, 60, .7), (25, 25, 2.0), (-75, -30, 1.2)], sawpit=(-35, -45)),
    }
    for name, st in stages.items():
        P = Part(name)
        for x, y, yaw in st['trunks']:
            trunk(P, r, x + r.uniform(-3, 3), y + r.uniform(-3, 3), yaw)
        for x, y in st['stumps']:
            stump(P, r, x + r.uniform(-3, 3), y + r.uniform(-3, 3))
        for x, y, yaw in st['stacks']:
            stack(P, r, x, y, yaw)
        if 'sawpit' in st:
            sawpit(P, r, *st['sawpit'])
    occlude()
