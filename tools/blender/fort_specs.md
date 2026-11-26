# Chapter III (James Fort, May-June 1607) - asset specs for asset_job.py

The ships are NOT here: the game already builds the Susan Constant (and, scaled, her consorts) in
buildConsort(), and one ship should have one owner.

Directions are Blender's: +Z up, and **the river is toward -Y** in every asset. Palette (sRGB): fresh-split oak
#b08a5a, weathered timber #7d6a52, bark #4e3b2a, cut ends #c9a874, leaves #4f6b34 / #3e5a2a, dead brown leaves
#6e5a36, sailcloth #d8cfb4 (weathered #bdb39a), rope #8a7656, iron #3a3a3a, bare earth #6b5638, turned earth
#5a4630, green shoots #6f9a3c, stone #8a8478.

## brush_fence
out: fort/brush_fence.glb | nodes: brush_fence_1,brush_fence_2,brush_fence_3,brush_fence_4 | budget: 14000 | grounded: yes
On 26 May 1607 the colonists' only defence was "the boughs of trees cast together in the form of a half moon"
(John Smith). Build a HALF-MOON (a half circle, radius 110 ft, centred on the origin) of piled, tangled cut boughs
and brush, 4-5 ft high and 5 ft thick. The half circle bulges toward +Y; its two open ends are at x=-110 and x=+110
on y=0 (the open side faces the river at -Y). Split the arc into four equal quarters by angle, one Part each,
brush_fence_1 the first quarter from the x=-110 end through brush_fence_4 ending at x=+110. Each quarter: a few
long bough trunks lying along the arc (Part.log, bark colour, lying near z=0.5 to 2, slightly crossed), plus many
Part.branch_spray boughs pointing outward and upward at varied angles, some with dead brown leaves. It must read
as a rough, uneven heap, NOT a neat hedge - and it must be CONTINUOUS: a man could not see or walk through
it anywhere along the arc. Place a bough every 2 to 3 feet of arc (about 40 per quarter), crossing and
overlapping, at three heights (lying near z=0.5, leaning at z=1.5-3, and on top reaching z=4-5), plus 6-8
long trunks per quarter. Keep it within budget: use depth=1 branch_sprays with short lengths (4-7 ft).

## fort_palisade
out: fort/fort_palisade.glb | nodes: palisade_river,palisade_east,palisade_west,bulwark_sw,bulwark_se,bulwark_n,gate | budget: 32000 | grounded: yes
James Fort as finished 15 June 1607: "triangle wise, having three bulwarks at every corner like a half moon, and
four or five pieces of artillery mounted in them" (George Percy). The river side is 420 ft long on y=0 from
x=-210 to x=+210; the other two sides are 300 ft each, meeting at an apex at about (0, 222). Walls are a palisade
of split timbers set upright side by side: each post a Part.board about 1.1 ft wide, 0.5 ft thick, 11-12 ft tall
(vary height by up to 0.8 ft and lean by up to 2 degrees), flat face outward, set from z=-0.3; one horizontal rail
(Part.log, small) along the inside at 8 ft. Space posts every 1.15 ft (no gaps). Leave a 10 ft GATE gap in the
middle of the river side; Part gate = two heavy board gate leaves standing open inward plus two tall gate posts.
At each corner a BULWARK (bulwark_sw at x=-210,y=0; bulwark_se at x=+210,y=0; bulwark_n at the apex): a circle
about 50 ft across of the same palisade posts (leave the side facing the fort's inside open), with an earth
platform inside (Part.mound, radius 20, height 4, earth colour) and a plank gun platform on it (the guns are not in this model: they are the saker asset, placed by the game).
palisade_river/east/west are the three walls between the bulwarks. To fit the budget, posts can be 4-sided boards
(they are) and rails 6 sides.

## awning
out: fort/awning.glb | nodes: awning | budget: 2600 | grounded: yes
The first church, from John Smith: "we did hang an awning (which is an old sail) to three or four trees to shadow
us from the sun, our walls were rails of wood, our seats unhewed trees till we cut planks, our pulpit a bar of wood
nailed to two neighbouring trees." Origin at the centre, about 40 x 30 ft. Four tree trunks (Part.log bark, radius
1.0 tapering to 0.6, 26 ft tall, with 2-3 stub branches each and a few big leaf tufts at the top) at the corners
(about (+-18, +-13)). Between them an old sail sagging like a hammock (Part.surface, weathered sailcloth): corners
tied at about z=11 to the trunks, sagging to about z=8.5 in the middle, slightly uneven. Short ropes (thin logs)
from each sail corner to its trunk. Split-rail walls (two rails, Part.log radius 0.25, on short forked posts) along
the two long sides. Four or five rows of log seats (Part.log lying on the ground, radius 0.7, 12 ft long, cut ends
lighter) facing +X. At the +X end the pulpit: a bar (Part.board) at 4 ft height nailed between two of the trunks or
two posts. Part awning is everything.

## camp
out: fort/camp.glb | nodes: camp_shelters,camp_fire,camp_casks,camp_casks_open | budget: 9000 | grounded: yes
The men's shelters in the first weeks, over about 120 x 80 ft, origin at the centre. camp_shelters: 8 rough
A-shaped shelters, each a sailcloth sheet (Part.surface, slightly sagging) draped over a ridge pole (Part.log)
between two forked sticks, 7 ft high, 10-14 ft long, ends open, scattered at different angles in a loose cluster
(not a grid). camp_fire: a ring of 8 stones (Part.box, small, stone colour, varied) with charred logs inside and an
iron pot hanging from a tripod of three poles. camp_casks: at about (40, -25), six closed barrels ("dry fats"; the
arms were packed in casks) - each barrel a Part.log with 10 sides, bulging (build it from two logs meeting at the
middle: radius 1.0 at the ends, 1.2 at the middle), 3 ft tall, standing upright, hoops as dark thin bands (a
slightly larger short log in iron colour near each end) - plus two chests (Part.box). camp_casks_open: the SAME six
barrels in the same places but with the tops off (lids lying on the ground beside them) and matchlocks leaning
against them: each matchlock a long thin Part.log (barrel, iron) plus a wooden stock (Part.board), 5 ft long, about
eight leaning at varied angles, and three pikes (Part.log 14 ft, thin, with a small iron point) leaning together.

## clearing
out: fort/clearing.glb | nodes: clearing_1,clearing_2,clearing_3 | budget: 8500 | grounded: yes
Ground being cleared of forest, about 200 x 150 ft, origin at the centre. Three progress stages; each Part adds
MORE, in different places (they are all shown together at the last stage): felled tree trunks (Part.log, radius
1.0-1.4 tapering, 30-50 ft long, lying on the ground at z about radius, varied directions, with a few stub branches
and the cut end lighter), stumps (Part.log, short, 1.5-2.5 ft tall, radius 1.0-1.5, cut tops lighter #c9a874, a
few roots as short logs splaying out), and stacks of riven clapboard (the Company wanted clapboard as a return
cargo): each stack = two cross skids (logs) with 6-10 layers of thin boards (Part.board 5 ft x 0.6 ft x 0.15 ft)
laid neatly across them. clearing_1: 4 trunks, 6 stumps, 1 stack. clearing_2: 4 trunks, 7 stumps, 2 stacks.
clearing_3: 3 trunks, 7 stumps, 3 stacks, plus a sawpit (a rectangular pit edge of logs with a log across it).

## storehouse
out: fort/storehouse.glb | nodes: storehouse_frame,storehouse_walls,storehouse_roof | budget: 4200 | grounded: yes
A timber-framed storehouse, 40 ft along X by 20 ft along Y, origin at the centre. storehouse_frame: sills
(Part.board lying), corner and middle posts (Part.board upright, 0.7 ft square, 9 ft tall), top plates, and rafters
(pairs meeting at a ridge 17 ft high), a door gap on the -Y side. storehouse_walls: riven boards (Part.board,
overlapping clapboard, slightly varied) filling the walls between the posts, leaving the door gap. storehouse_roof:
a thick thatch roof (two sloped slabs built with Part.quad, 1.2 ft thick, overhanging 2 ft, colour #8a7448 with a
darker underside) over the rafters, and ridge.

## cornfield
out: fort/cornfield.glb | nodes: cornfield_1,cornfield_2 | budget: 14000 | grounded: yes
A planted patch about 120 x 80 ft, origin at the centre. cornfield_1: rows of corn hills - small mounds of turned
earth (Part.mound, radius 1.2, height 0.6, 6 sides, 2 rings) in loose rows about 4 ft apart, slightly irregular
(not a perfect grid), plus a short rail fence (a few forked posts and two rails) along the +Y side. cornfield_2:
young green shoots on each hill (2-3 small thin tapered leaves per hill, Part.tri or tiny Part.log, green, 1 ft
tall), in the same hill positions as cornfield_1 (compute the hill positions with the same seed in both).

## saker
out: fort/saker.glb | nodes: saker,saker_truck | budget: 3000 | grounded: yes
Written by Claude (2026-11-26), not by a local model; the spec is the header for build_one.py. A saker of about
1600: a cast muzzle-loader about 9 ft 6 in long, 3 1/2 in bore, a ball of about 5 lb, the trunnions over the origin
and the muzzle toward +Y. Two Parts with the same barrel: saker on a two-wheeled field carriage with a trail (the
gun the player may land and mount at the boughs before 26 May, the counterfactual), saker_truck on a ship's
four-truck carriage (the ships' ordnance mounted in the bulwarks by 15 June). Under 1,500 triangles each.
