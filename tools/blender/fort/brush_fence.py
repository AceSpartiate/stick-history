def build():
    R = rng(42)
    radius = 110.0
    bark = '#4e3b2a'
    leaf = '#4f6b34'
    dead_leaf = '#8b6914'
    trunk_bark = '#5a4630'
    cap_wood = '#c9a874'

    # Quarter angle ranges: π → 0 through π/2 (bulge toward +Y)
    quarters = [
        (math.pi, 3 * math.pi / 4),
        (3 * math.pi / 4, math.pi / 2),
        (math.pi / 2, math.pi / 4),
        (math.pi / 4, 0.0),
    ]

    n_boughs = 26
    n_trunks = 6

    for qi, (a0, a1) in enumerate(quarters):
        p = Part(f"brush_fence_{qi + 1}")
        Rq = rng(1000 + qi * 7919)
        span = a0 - a1  # π/4

        # --- Long trunks lying along the arc ---
        for ti in range(n_trunks):
            t = (ti + 0.5) / n_trunks
            theta = a0 - t * span + Rq.uniform(-0.015, 0.015)

            length = Rq.uniform(9, 14)
            dtheta = length / radius

            th_s = theta - dtheta * 0.5
            th_e = theta + dtheta * 0.5

            # Slight crossing: radial offsets differ at each end
            r_s = radius + Rq.uniform(-2.0, 2.0)
            r_e = radius + Rq.uniform(-2.0, 2.0)

            z_s = Rq.uniform(0.3, 0.7)
            z_e = Rq.uniform(0.3, 0.7)

            a = Vector((r_s * math.cos(th_s), r_s * math.sin(th_s), z_s))
            b = Vector((r_e * math.cos(th_e), r_e * math.sin(th_e), z_e))

            r0 = Rq.uniform(0.18, 0.28)
            r1 = Rq.uniform(0.10, 0.16)
            twist = Rq.uniform(0, math.pi)

            p.log(a, b, r0, r1, col=trunk_bark, sides=6, caps=True,
                  cap_col=cap_wood, twist=twist)

        # --- Branch sprays (the tangled bough mass) ---
        for bi in range(n_boughs):
            t = (bi + 0.5) / n_boughs
            theta = a0 - t * span + Rq.uniform(-0.025, 0.025)

            # Three height bands: low / mid / top
            band = Rq.random()
            if band < 0.40:
                z = Rq.uniform(0.3, 0.9)
            elif band < 0.75:
                z = Rq.uniform(1.2, 2.8)
            else:
                z = Rq.uniform(3.0, 4.8)

            # Radial position within the 5-ft-thick fence
            r = radius + Rq.uniform(-2.2, 2.2)

            base = Vector((r * math.cos(theta), r * math.sin(theta), z))

            # Direction: mostly outward + upward, some inward for tangle
            outward = Vector((math.cos(theta), math.sin(theta), 0.0))
            up = Vector((0.0, 0.0, 1.0))

            if Rq.random() < 0.22:
                # Inward-leaning bough
                direction = (-outward * Rq.uniform(0.25, 0.55)
                             + up * Rq.uniform(0.35, 0.65)).normalized()
            else:
                direction = (outward * Rq.uniform(0.35, 0.80)
                             + up * Rq.uniform(0.20, 0.70)).normalized()

            length = Rq.uniform(4.0, 7.0)
            r_branch = Rq.uniform(0.07, 0.14)

            # ~30 % dead brown leaves
            leaf_c = dead_leaf if Rq.random() < 0.30 else leaf

            p.branch_spray(base, direction, length, r_branch, Rq,
                           col=bark, leaf=leaf_c, forks=2, depth=1)

    occlude()
