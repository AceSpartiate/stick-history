# The storehouse, 40 x 20 ft, in three stages: frame, clapboard walls, thatched roof. Written by Claude, 2026-11-25.
OAK, OLD, CUT, THATCH, THATCH_UNDER = '#b08a5a', '#9a7b52', '#c9a874', '#8a7448', '#5e4e30'
X, Y, PLATE, RIDGE = 20.0, 10.0, 9.0, 17.0
DOOR = (-2.6, 2.6, 7.2)            # door gap on the -Y wall: x from, x to, height


def build():
    r = rng(1607)
    F = Part('storehouse_frame')
    s = 0.7
    for y in (-Y, Y):                                   # sills and top plates along the long sides
        F.board((-X - .4, y, s / 2), (X + .4, y, s / 2), s, s, OLD, up=(0, 1, 0))
        F.board((-X - .4, y, PLATE + s / 2), (X + .4, y, PLATE + s / 2), s, s, OAK, up=(0, 1, 0))
    for x in (-X, X):                                   # and across the ends
        F.board((x, -Y, s / 2), (x, Y, s / 2), s, s, OLD, up=(1, 0, 0))
        F.board((x, -Y, PLATE + s / 2), (x, Y, PLATE + s / 2), s, s, OAK, up=(1, 0, 0))
    posts = [(x, y) for x in (-X, -10, 0, 10, X) for y in (-Y, Y)] + [(x, 0) for x in (-X, X)]
    posts = [p for p in posts if not (p[1] == -Y and DOOR[0] < p[0] < DOOR[1])]
    posts += [(DOOR[0] - .35, -Y), (DOOR[1] + .35, -Y)]
    for x, y in posts:
        F.board((x, y, 0), (x, y, PLATE), s, s, OAK, up=(0, 1, 0))
    F.board((DOOR[0] - .7, -Y, DOOR[2]), (DOOR[1] + .7, -Y, DOOR[2]), .55, .55, OAK, up=(0, 1, 0))   # door head
    for k in range(9):                                  # rafter pairs to the ridge
        x = -X + k * 5
        for sg in (-1, 1):
            F.board((x, sg * (Y + .2), PLATE + s), (x, 0, RIDGE), .45, .35, OAK, up=(1, 0, 0))
    F.board((-X - .3, 0, RIDGE), (X + .3, 0, RIDGE), .5, .5, OAK, up=(0, 0, 1))
    for x in (-X, X):                                   # gable studs and collar
        F.board((x, -4, PLATE + s), (x, -4, PLATE + 4.6), .4, .4, OAK, up=(1, 0, 0))
        F.board((x, 4, PLATE + s), (x, 4, PLATE + 4.6), .4, .4, OAK, up=(1, 0, 0))

    W = Part('storehouse_walls')
    row = 0.72
    def wall(a, b, face, z0=0.6, z1=PLATE, gap=None):
        """Clapboards from a to b (horizontal ends), rows overlapping, each tipped out at its foot."""
        n = int((z1 - z0) / row)
        for i in range(n):
            z = z0 + i * row + row / 2
            off = face * (0.38 + .05 * r.random())
            pa, pb = Vector(a) + off, Vector(b) + off
            pa.z = pb.z = z
            if gap and z < gap[2]:
                for (u0, u1) in ((pa.x, gap[0]), (gap[1], pb.x)):
                    W.board((u0, pa.y, z), (u1, pb.y, z + r.uniform(-.04, .04)), row * 1.25, .1,
                            OLD if r.random() < .3 else OAK, up=(face.x, face.y, -0.25))
            else:
                W.board(pa, (pb.x, pb.y, z + r.uniform(-.04, .04)), row * 1.25, .1, OLD if r.random() < .3 else OAK,
                        up=(face.x, face.y, -0.25))
    for bay in range(4):
        x0, x1 = -X + bay * 10, -X + bay * 10 + 10
        wall((x0, -Y, 0), (x1, -Y, 0), Vector((0, -1, 0)), gap=DOOR if x0 < 0 < x1 else None)
        wall((x0, Y, 0), (x1, Y, 0), Vector((0, 1, 0)))
    for x, sg in ((-X, -1), (X, 1)):
        for y0, y1 in ((-Y, 0), (0, Y)):
            # the end walls, then the gable triangle above the plate in shortening rows
            n = int((PLATE - .6) / row)
            for i in range(n):
                z = .6 + i * row + row / 2
                W.board((x + sg * .4, y0, z), (x + sg * .4, y1, z), row * 1.25, .1, OLD if r.random() < .3 else OAK,
                        up=(sg, 0, -0.25))
        z = PLATE + .7
        while z < RIDGE - .6:
            half = Y * (RIDGE - z) / (RIDGE - PLATE) - .2
            W.board((x + sg * .4, -half, z), (x + sg * .4, half, z), row * 1.25, .1, OAK, up=(sg, 0, -0.25))
            z += row

    R = Part('storehouse_roof')
    over, th = 2.0, 1.2
    slope = (RIDGE - PLATE) / Y
    eave_y, eave_z = Y + over, PLATE + s - over * slope
    top_z = RIDGE + s
    courses, segs = 6, 8
    shades = [THATCH, '#7d6a40', '#958050', '#84703f', THATCH, '#8f7a4a']
    for sg in (-1, 1):
        for i in range(courses):
            # each course a band of thatch from its butt (thick, proud) up under the next course
            f0, f1 = i / courses, min(1.0, (i + 1.35) / courses)
            def pt(x, f, lift):
                return Vector((x, sg * eave_y * (1 - f), eave_z + (top_z - eave_z) * f + lift + .45))   # clear of the rafters
            xs = [-X - over + (2 * (X + over)) * k / segs for k in range(segs + 1)]
            jig = [r.uniform(-.18, .18) for _ in xs]
            butt = 0.55 + .1 * r.random()
            for k in range(segs):
                a0, a1 = pt(xs[k], f0, butt + jig[k]), pt(xs[k + 1], f0, butt + jig[k + 1])
                c0, c1 = pt(xs[k], f1, .15), pt(xs[k + 1], f1, .15)
                l0, l1 = pt(xs[k], f0, -th * .5 + jig[k]), pt(xs[k + 1], f0, -th * .5 + jig[k + 1])
                col = shades[(i + k // 3) % len(shades)]
                if sg > 0:
                    R.quad(a0, a1, c1, c0, col)
                    R.quad(l0, l1, a1, a0, '#6e5c38')            # the butt end, facing down-slope
                else:
                    R.quad(a0, c0, c1, a1, col)
                    R.quad(l0, a0, a1, l1, '#6e5c38')
            if i == 0:                                           # the dark underside, seen from below the eaves
                u0, u1 = pt(-X - over, 0, -th * .5), pt(X + over, 0, -th * .5)
                u2, u3 = pt(X + over, 1, -th * .5), pt(-X - over, 1, -th * .5)
                R.quad(u0, u3, u2, u1, THATCH_UNDER) if sg > 0 else R.quad(u0, u1, u2, u3, THATCH_UNDER)
    R.log((-X - over, 0, top_z + .9), (X + over, 0, top_z + .9), .8, .75, '#6e5c38', sides=6)
    occlude(height=9)
