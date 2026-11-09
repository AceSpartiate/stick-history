def build():
    SEED = 42
    P1 = Part('cornfield_1')
    P2 = Part('cornfield_2')

    def gen_hills(R):
        pos = []
        nx = 6
        ny = 10
        x_start = -35.0
        x_spacing = 14.0
        y_start = -50.0
        y_spacing = 11.0
        for i in range(ny):
            for j in range(nx):
                x = x_start + j * x_spacing + R.uniform(-0.6, 0.6)
                y = y_start + i * y_spacing + R.uniform(-0.6, 0.6)
                pos.append((x, y))
        return pos

    # ── cornfield_1: mounds + forked round-timber fence along +Y ──
    R1 = rng(SEED)
    hills = gen_hills(R1)

    for (hx, hy) in hills:
        r = 0.9 + R1.uniform(-0.05, 0.05)
        h = 0.5 + R1.uniform(-0.04, 0.04)
        P1.mound(center=(hx, hy, 0.0), radius=r, height=h, col='#5a4630', sides=5, rings=1)

    # Fence along +Y side (y = +40), spanning the 120 ft long edge
    fy = 40.0
    fence_xs = [-50.0, -25.0, 0.0, 25.0, 50.0]
    for fx in fence_xs:
        lean = R1.uniform(-0.03, 0.03)
        h = R1.uniform(5.0, 6.0)
        r0 = 0.4 + R1.uniform(-0.03, 0.03)
        a = (fx + lean, fy, -0.2)
        b = (fx - lean * 0.5, fy, h)
        P1.log(a, b, r0, r0 * 0.5, col='#7d6a52', col1='#6b5c44',
               sides=6, caps=True, cap_col='#c9a874', twist=R1.uniform(0, 3.14))

        # Forked top: two thick round-timber prongs splaying up
        top = (fx - lean * 0.5, fy, h)
        spread = R1.uniform(0.5, 0.7)
        fork_h = R1.uniform(1.2, 1.6)
        fr0 = r0 * 0.55
        P1.log(top, (top[0] - spread, top[1], top[2] + fork_h), fr0, 0.08,
               col='#7d6a52', col1='#6b5c44', sides=5, caps=True, cap_col='#c9a874')
        P1.log(top, (top[0] + spread, top[1], top[2] + fork_h), fr0, 0.08,
               col='#7d6a52', col1='#6b5c44', sides=5, caps=True, cap_col='#c9a874')

    # Two round-timber rails along +Y, supported by posts
    P1.log((-55, fy, 1.5), (55, fy, 1.5), 0.25, 0.25, col='#8a7a5a',
           sides=6, caps=True, cap_col='#c9a874')
    P1.log((-55, fy, 3.5), (55, fy, 3.5), 0.25, 0.25, col='#8a7a5a',
           sides=6, caps=True, cap_col='#c9a874')

    # ── cornfield_2: 3 visible tapered blades per hill ──
    R2 = rng(SEED)
    hills2 = gen_hills(R2)

    for (hx, hy) in hills2:
        for k in range(3):
            angle = R2.uniform(0, 6.28)
            dist = R2.uniform(0.05, 0.2)
            ox = hx + dist * math.cos(angle)
            oy = hy + dist * math.sin(angle)
            base_z = 0.35
            length = R2.uniform(1.2, 1.6)
            lean_angle = R2.uniform(0.3, 0.7)
            lean_dir = R2.uniform(0, 6.28)
            tx = ox + math.cos(lean_dir) * math.sin(lean_angle) * length
            ty = oy + math.sin(lean_dir) * math.sin(lean_angle) * length
            tz = base_z + math.cos(lean_angle) * length
            P2.log((ox, oy, base_z), (tx, ty, tz), 0.12, 0.02,
                   col='#6f9a3c', col1='#8ab34a', sides=5, caps=False)

    occlude()
