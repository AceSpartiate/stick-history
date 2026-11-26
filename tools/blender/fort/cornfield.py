# Corn ground, about 120 x 80 ft: hills of turned earth in loose rows (stage 1), then young shoots on every hill
# (stage 2), and a short rail fence on the +Y side. Written by Claude, 2026-11-25 (replaces the local model's draft).
EARTH, EARTH2, SHOOT, SHOOT2, POLE, CUT = '#5a4630', '#4e3c28', '#6f9a3c', '#5d8a32', '#7d6a52', '#c9a874'


def hills():
    r = rng(1612)                       # the same seed in both stages: the shoots stand on the hills
    out = []
    for row in range(20):
        y = -38 + row * 4 + r.uniform(-.5, .5)
        x = -58 + r.uniform(0, 2)
        while x < 58:
            out.append((x + r.uniform(-.4, .4), y + r.uniform(-.5, .5), r.uniform(.85, 1.15)))
            x += r.uniform(3.6, 4.6)
    return out


def build():
    r = rng(1607)
    H = hills()
    A = Part('cornfield_1')
    for x, y, s in H:
        A.mound((x, y, -0.05), 1.1 * s, .55 * s, EARTH if r.random() < .6 else EARTH2, sides=5, rings=2)
    for k in range(7):                                   # a short rail fence along +Y
        x = -60 + k * 20
        A.log((x, 42, -.3), (x, 42, 3.8), .2, .16, POLE, sides=5, cap_col=CUT, twist=r.random())
        for s in (-1, 1):
            A.log((x, 42, 3.2), (x + s * .4, 42, 4.1), .08, .06, POLE, sides=4, caps=False)
    for z in (1.8, 3.5):
        A.log((-61, 42, z), (61, 42, z + r.uniform(-.1, .1)), .22, .2, POLE, sides=6, cap_col=CUT)

    B = Part('cornfield_2')
    for x, y, s in H:
        top = Vector((x, y, .5 * s))
        for k in range(3):
            a = r.uniform(0, 6.28)
            L = r.uniform(1.2, 1.6)
            d = Vector((math.cos(a) * .45, math.sin(a) * .45, 1)).normalized()
            w = Vector((-math.sin(a), math.cos(a), 0)) * .07
            tip = top + d * L + Vector((math.cos(a), math.sin(a), 0)) * .25        # blades arch outward
            col = SHOOT if k % 2 else SHOOT2
            B.tri(top - w, top + w, tip, col)
            B.tri(top + w, top - w, tip, col)
    occlude(ground=.7, height=2)
