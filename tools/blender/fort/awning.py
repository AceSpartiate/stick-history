# The first church at Jamestown (John Smith): an old sail hung to trees, rails of wood for walls, unhewed trees for
# seats, a bar of wood nailed to two trees for a pulpit. Written by Claude, 2026-11-25.
BARK, SAIL, ROPE, POLE, CUT, LEAF, LEAF2 = '#4e3b2a', '#bdb39a', '#8a7656', '#7d6a52', '#c9a874', '#4f6b34', '#3e5a2a'


def tree(P, r, x, y, h=26):
    base, top = Vector((x, y, -0.5)), Vector((x + r.uniform(-1, 1), y + r.uniform(-1, 1), h))
    P.log(base, top, 1.0, 0.55, BARK, sides=8, twist=r.random())
    for k in range(3):                       # roots flaring
        a = r.random() * 6.28
        P.log((x, y, 0.8), (x + math.cos(a) * 2.6, y + math.sin(a) * 2.6, -0.2), 0.5, 0.2, BARK, sides=5, caps=False)
    crown = []
    for k in range(4):                       # limbs, then a crown of overlapping leaf masses on and between them
        a = k * 1.57 + r.uniform(-.4, .4)
        z = h * r.uniform(.62, .9)
        st = Vector((x, y, z))
        end = st + Vector((math.cos(a) * r.uniform(6, 9), math.sin(a) * r.uniform(6, 9), r.uniform(2, 5)))
        P.log(st, end, 0.35, 0.15, BARK, sides=5, caps=False)
        crown += [end, (st + end) / 2 + Vector((0, 0, 2.5))]
    crown.append(top + Vector((0, 0, 1)))
    for c in crown:
        P.tuft(c + Vector((r.uniform(-1, 1), r.uniform(-1, 1), 0)), r.uniform(7, 10), r, LEAF if r.random() < .6 else LEAF2)


def build():
    r = rng(1607)
    P = Part('awning')
    corners = [(-18, -13), (18, -13), (18, 13), (-18, 13)]
    for i, (x, y) in enumerate(corners):
        tree(P, rng(i + 5), x + r.uniform(-1.5, 1.5), y + r.uniform(-1, 1))
    # the old sail: tied at about 11 ft to the four trunks, sagging to 8.5 in the middle
    tie = 11.0

    def sail(u, v):
        x, y = -16.6 + u * 33.2, -11.8 + v * 23.6
        z = tie - 2.5 * math.sin(math.pi * u) * math.sin(math.pi * v) + 0.25 * math.sin(u * 9 + v * 4)
        return (x, y, z)
    P.surface(sail, 8, 6, SAIL)
    for x, y in corners:                     # ropes, sail corner to trunk
        sx, sy = math.copysign(16.6, x), math.copysign(11.8, y)
        P.log((sx, sy, tie), (x * 0.97, y * 0.95, tie + 0.6), 0.06, 0.06, ROPE, sides=4)
    # split-rail walls along the long sides
    for y in (-14.5, 14.5):
        posts = [-15, -5, 5, 15]
        for px in posts:
            P.log((px, y, -0.3), (px, y, 3.6), 0.2, 0.16, POLE, sides=5, twist=r.random())
            for s in (-1, 1):
                P.log((px, y, 3.1), (px + s * 0.4, y, 3.9), 0.08, 0.06, POLE, sides=4, caps=False)
        for z in (1.6, 3.4):
            P.log((-16, y, z + r.uniform(-.1, .1)), (16, y, z + r.uniform(-.1, .1)), 0.25, 0.22, POLE, sides=6,
                  cap_col=CUT)
    # unhewed trees for seats, rows facing +X
    for k, x in enumerate((-12, -8, -4, 0, 4)):
        L = r.uniform(11, 13)
        y0 = r.uniform(-1, 1)
        P.log((x, y0 - L / 2, 0.55), (x + r.uniform(-.4, .4), y0 + L / 2, 0.55), 0.7, 0.6, BARK, sides=7, cap_col=CUT,
              twist=r.random())
    # the pulpit: a bar of wood nailed to two posts at the +X end
    for y in (-2.2, 2.2):
        P.log((12.5, y, -0.3), (12.5, y, 5.2), 0.3, 0.26, POLE, sides=6, cap_col=CUT)
    P.board((12.3, -2.6, 4.0), (12.3, 2.6, 4.0), 0.6, 0.25, '#9a7b52')
    occlude()
