# A saker of about 1600, and the two carriages Chapter III puts it on. Written by Claude, 2026-11-26.
#
# The piece: a muzzle-loader of about 9 1/2 ft, a 3 1/2 in bore, a ball of about 5 lb (a saker's shot is the
# game's SAKER constant: 3 1/2 in across). Cast iron, as a merchant ship's ordnance most likely was; the
# profile is the usual one - cascabel, base ring, two reinforces, the trunnions at three sevenths of the
# length from the base ring, a tapering chase, a swelling at the muzzle - and the bore is open at the muzzle.
# Every dimension is written in INCHES (and turned to feet at IN), so it can be checked against a catalogue.
#
#   saker        on a two-wheeled field carriage with a trail: the gun the player can have landed and
#                mounted at the boughs before 26 May (the counterfactual; the record has every gun aboard)
#   saker_truck  on a ship's four-truck carriage: the ships' ordnance landed and mounted in the half-moon
#                bulwarks by 15 June (Percy: "foure or five pieces of Artillerie mounted in them")
#
# Directions: the muzzle points along +Y (in the game, -z: away from the river), the trunnions sit over the
# origin, the ground is z=0.
IN = 1 / 12
IRON, IRON_HI, BORE = '#46443f', '#58564f', '#121110'
WOOD, WOOD_DK, CUT, STRAP = '#6b5236', '#56422c', '#a88a5e', '#2c2b29'

# Barrel profile: (inches from the base ring's back face toward the muzzle, radius in inches). A step is two
# rings at the same station. Breech 12 in across, muzzle swell about 9 in, chase down to 7 1/4 in at the neck.
PROFILE = [(-7.6, 0.0), (-7.1, 1.5), (-5.6, 2.1), (-4.1, 1.2), (-2.6, 2.8), (-0.6, 5.2), (0.0, 6.0),
           (0.0, 6.35), (1.6, 6.35), (1.6, 5.9),                 # base ring, then the first reinforce
           (28.0, 5.6), (28.0, 5.95), (29.6, 5.95), (29.6, 5.4),  # a ring, then the second reinforce
           (53.0, 5.05), (53.0, 5.3), (54.6, 5.3), (54.6, 4.6),   # the reinforce ring, then the chase
           (103.5, 3.65), (107.5, 4.3), (111.5, 4.45), (114.0, 4.15)]
LENGTH = 114.0                       # base ring to muzzle face, 9 ft 6 in
TRUN = LENGTH * 3 / 7                # trunnions 48.9 in from the base ring
BORE_R = 1.75                        # 3 1/2 in bore
SIDES = 12


def lathe(P, axis_o, ax, prof, sides, col_fn):
    """Turn a (station, radius) profile about the axis through axis_o along unit vector ax. Returns the rings.
    Stations rising give outward faces; a ring stepping inward at one station faces along +ax; stations falling
    at a small radius line a bore, facing in."""
    u = ax.cross(Vector((1, 0, 0)) if abs(ax.x) < 0.9 else Vector((0, 0, 1))).normalized()
    w = ax.cross(u).normalized()
    rings = []
    for s, r in prof:
        c = axis_o + ax * s
        rings.append([c + (u * math.cos(2 * math.pi * (k + .5) / sides) + w * math.sin(2 * math.pi * (k + .5) / sides))
                      * r for k in range(sides)])
    for i in range(len(rings) - 1):
        (s0, r0), (s1, r1) = prof[i], prof[i + 1]
        col = col_fn(s0, s1, r0, r1)
        for k in range(sides):
            n = (k + 1) % sides
            if r0 == 0:
                P.tri(rings[i][k], rings[i + 1][n], rings[i + 1][k], col)   # the cascabel's point
            else:
                P.quad(rings[i][k], rings[i][n], rings[i + 1][n], rings[i + 1][k], col)
    return rings


def barrel(P, trunnion_at, elev_deg=2.0):
    """The piece, its trunnions at trunnion_at, the muzzle along +Y raised by elev_deg."""
    e = math.radians(elev_deg)
    ax = Vector((0, math.cos(e), math.sin(e)))
    o = trunnion_at - ax * (TRUN * IN)          # the base ring's back face

    def col(s0, s1, r0, r1):
        if max(r0, r1) <= BORE_R * IN + 1e-6:
            return BORE                                 # down the bore
        if s0 == s1:
            return IRON_HI if r1 > r0 else IRON         # the face of a ring catches the light
        return IRON_HI if (s1 - s0) < 2.0 * IN and r0 > 5 * IN else IRON
    # the profile, then the muzzle face and six inches of open bore going into the dark
    prof = [(s * IN, r * IN) for s, r in PROFILE + [(LENGTH, BORE_R), (LENGTH - 6, BORE_R)]]
    rings = lathe(P, o, ax, prof, SIDES, col)
    P._face(rings[-1], BORE)
    # trunnions, 3 1/2 in across and as long, a touch below the axis as they were cast
    for s in (-1, 1):
        c = trunnion_at + Vector((0, 0, -0.6 * IN))
        x0 = 4.9 * IN                                 # just inside the second reinforce's surface
        P.log(c + Vector((s * x0, 0, 0)), c + Vector((s * (x0 + 3.5 * IN), 0, 0)), 1.75 * IN, 1.75 * IN, IRON,
              sides=8, cap_col=IRON_HI)
    # the dolphins (lifting handles) over the trunnions: two small iron loops, as blocks
    for s in (-1, 1):
        b = trunnion_at + ax * (4 * IN) + Vector((s * 2.2 * IN, 0, 5.0 * IN))
        P.board(b - ax * (3 * IN), b + ax * (3 * IN), 1.0 * IN, 2.2 * IN, IRON, up=(1, 0, 0))


def cheek(P, prof, x_at, thick, col):
    """A carriage cheek: the (y, z) outline prof (counter-clockwise seen from +X), as a plank thick across X,
    its centre line at x_at(y) so a trail can draw in."""
    n = len(prof)
    outer = [Vector((x_at(y) + thick / 2, y, z)) for y, z in prof]
    inner = [Vector((x_at(y) - thick / 2, y, z)) for y, z in prof]
    P._face(outer, col)
    P._face(list(reversed(inner)), col)
    for k in range(n):
        m = (k + 1) % n
        P.quad(inner[k], inner[m], outer[m], outer[k], col)


def wheel(P, at, r, width, spokes=8, segs=14):
    """A spoked wheel turning about X: rim, spokes, hub."""
    depth = 3.5 * IN
    for k in range(segs):
        a0, a1 = 2 * math.pi * k / segs, 2 * math.pi * (k + 1) / segs
        pt = lambda a, rr, dx: at + Vector((dx, math.cos(a) * rr, math.sin(a) * rr))
        o0, o1 = pt(a0, r, 0), pt(a1, r, 0)
        hw = width / 2
        A = [pt(a0, r, -hw), pt(a1, r, -hw), pt(a1, r, hw), pt(a0, r, hw)]
        B = [pt(a0, r - depth, -hw), pt(a1, r - depth, -hw), pt(a1, r - depth, hw), pt(a0, r - depth, hw)]
        P.quad(A[0], A[1], A[2], A[3], STRAP)               # the iron tyre
        P.quad(B[3], B[2], B[1], B[0], WOOD_DK)
        P.quad(A[3], A[2], B[2], B[3], WOOD)                # felloe faces
        P.quad(B[0], B[1], A[1], A[0], WOOD)
    for k in range(spokes):
        a = 2 * math.pi * (k + .25) / spokes
        d = Vector((0, math.cos(a), math.sin(a)))
        P.board(at + d * (3 * IN), at + d * (r - depth + .02), 2.6 * IN, 1.6 * IN, WOOD, up=(1, 0, 0))
    s = 1 if at.x > 0 else -1
    P.log(at - Vector((s * 4.5 * IN, 0, 0)), at + Vector((s * 6.5 * IN, 0, 0)), 4.8 * IN, 3.6 * IN, WOOD_DK,
          sides=8, cap_col=STRAP)


def field_carriage():
    P = Part('saker')
    R = 27 * IN                                      # wheels 4 ft 6 in
    TRUN_Z = 40 * IN                                 # the trunnions 3 ft 4 in off the ground
    # cheeks 5 in thick, 13 in apart at the trunnions, drawing in to 8 in apart at the trail
    x_at = lambda y: 9 * IN - (max(0.0, -y) / 8.6) * 2.5 * IN
    prof = [(1.25, 1.85), (-1.2, 1.72), (-7.7, 0.0), (-8.6, 0.0), (-8.6, 0.45), (-8.45, 0.62), (-2.5, 2.38),
            (-2.4, 2.63), (-0.62, 2.9), (-0.52, 3.18), (1.25, 3.12)]
    prof = [(y, z) for y, z in prof]
    for s in (-1, 1):
        cheek(P, prof, (lambda y, s=s: s * x_at(y)), 5 * IN, WOOD)
        # cap-square over the trunnion
        P.board(Vector((s * x_at(0), -4 * IN, TRUN_Z + 1.9 * IN)), Vector((s * x_at(0), 4 * IN, TRUN_Z + 1.9 * IN)),
                5.4 * IN, 1.0 * IN, STRAP)
    # axletree, wheels outside the cheeks
    P.box((0, 0, R - 3 * IN), (2 * (x_at(0) + 12 * IN), 6 * IN, 6 * IN), WOOD_DK)
    for s in (-1, 1):
        wheel(P, Vector((s * (x_at(0) + 9 * IN), 0, R)), R, 3.5 * IN)
    # transoms between the cheeks, the stool bed and the quoin under the breech, a trail transom
    for y, z, h in ((1.0, 2.05, 9), (-2.0, 2.0, 7), (-7.2, 0.45, 6)):
        P.box((0, y, z), (2 * x_at(y) - 4 * IN, 5 * IN, h * IN), WOOD_DK)
    P.box((0, -4.0, 1.66), (2 * x_at(-4.0) - 4 * IN, 16 * IN, 3 * IN), WOOD_DK)
    # the quoin: a wedge, thick end back
    y0, y1 = -4.55, -3.45
    zb, zf, zt = 1.91, 2.7, 2.95
    hw = x_at(-4.0) - 3.5 * IN
    pts = [Vector((-hw, y0, zb)), Vector((hw, y0, zb)), Vector((hw, y1, zb)), Vector((-hw, y1, zb)),
           Vector((-hw, y0, zt)), Vector((hw, y0, zt)), Vector((hw, y1, zf)), Vector((-hw, y1, zf))]
    for f in ((3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        P.quad(*[pts[i] for i in f], CUT if f == (4, 5, 6, 7) else WOOD)
    # an iron trail plate where it bears on the ground
    P.box((0, -8.35, 0.0), (2 * x_at(-8.35) + 5 * IN, 6 * IN, 1.0 * IN), STRAP)
    barrel(P, Vector((0, 0, TRUN_Z)), elev_deg=2.0)


def truck_carriage():
    P = Part('saker_truck')
    TRUN_Z = 29 * IN                                 # a ship's carriage sits low: trunnions 2 ft 5 in up
    x_at = lambda y: 9 * IN                          # brackets 5 in thick, 13 in apart
    prof = [(1.3, 0.62), (-3.6, 0.62), (-3.6, 1.33), (-2.75, 1.33), (-2.75, 1.68), (-1.7, 1.68), (-1.7, 2.0),
            (-0.6, 2.0), (-0.5, 2.3), (1.3, 2.3)]
    for s in (-1, 1):
        cheek(P, prof, (lambda y, s=s: s * x_at(y)), 5 * IN, WOOD)
        P.board(Vector((s * x_at(0), -4 * IN, TRUN_Z + 1.9 * IN)), Vector((s * x_at(0), 4 * IN, TRUN_Z + 1.9 * IN)),
                5.4 * IN, 1.0 * IN, STRAP)
    # the trucks: solid wooden wheels, the fore pair 15 in across and the hind pair 13 in
    for y, r in ((0.75, 7.5 * IN), (-3.0, 6.5 * IN)):
        P.box((0, y, r - 2.8 * IN), (2 * (x_at(y) + 7 * IN), 5.5 * IN, 5.5 * IN), WOOD_DK)    # axletree
        for s in (-1, 1):
            c = Vector((s * (x_at(y) + 4.5 * IN), y, r))
            P.log(c - Vector((s * 2.2 * IN, 0, 0)), c + Vector((s * 2.2 * IN, 0, 0)), r, r * .97, WOOD, sides=10,
                  cap_col=WOOD_DK)
            P.log(c + Vector((s * 2.2 * IN, 0, 0)), c + Vector((s * 3.6 * IN, 0, 0)), 1.6 * IN, 1.2 * IN, STRAP,
                  sides=6)                           # the linchpin end of the axle
    # transom at the front, the bed and the quoin under the breech
    P.box((0, 1.0, 0.95), (2 * x_at(1.0) - 4 * IN, 5 * IN, 9 * IN), WOOD_DK)
    P.box((0, -3.2, 0.62), (2 * x_at(-3.2) - 4 * IN, 2.2, 3 * IN), WOOD_DK)
    y0, y1 = -4.5, -3.35
    zb, zf, zt = 0.87, 1.5, 1.82
    hw = x_at(-4.0) - 3.5 * IN
    pts = [Vector((-hw, y0, zb)), Vector((hw, y0, zb)), Vector((hw, y1, zb)), Vector((-hw, y1, zb)),
           Vector((-hw, y0, zt)), Vector((hw, y0, zt)), Vector((hw, y1, zf)), Vector((-hw, y1, zf))]
    for f in ((3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        P.quad(*[pts[i] for i in f], CUT if f == (4, 5, 6, 7) else WOOD)
    barrel(P, Vector((0, 0, TRUN_Z)), elev_deg=0.0)


def build():
    field_carriage()
    truck_carriage()
    occlude(ground=0.62, height=3.5, under=0.7)
