# Stick History — Jamestown

A browser history game for 6th–8th grade Social Studies. One HTML file, Three.js
from CDN, no textures and no image assets.

## Run it

Open `index.html` in **Chrome or Safari** — a real browser, not an in-app viewer.
The Web Speech API used for narration is **not implemented in Android WebView**,
so read-aloud silently does nothing there. The game detects this and hides the
narration controls rather than offering dead buttons.

## Host it (recommended)

`index.html` is named for GitHub Pages, so:

1. Create a public repo and upload this folder
2. **Settings → Pages → Deploy from a branch →** `main` / `/root`
3. Open `https://<you>.github.io/<repo>/`

Hosting matters for more than convenience: `localStorage` is unreliable over
`file://`, so save-and-resume only works properly on a served page. Students on
different machines carry progress with the **Muster Code** in the pause menu.

## Check before committing

```
python3 tools/check.py
```

Eight checks, each corresponding to a bug that reached the player at least once —
unwired actions, unregistered modals, unguarded element reads, undefined calls,
over-long cutscenes, and accidental image assets.

## Read first

- `CLAUDE.md` — conventions, invariants, and the bug classes that recurred
- `docs/BUILD_PLAN.md` — status, settled decisions, phase order, open questions
- `docs/CHAPTER_2_DESIGN.md` — the original Chapter II design (§1–8 still stand)

## Where things stand

Phases 0, 1, 2 and 2.5 complete. Chapter I (the bay mouth, dawn 26 April 1607)
and Chapter II (Cape Henry, that afternoon) are playable. **Phase 3** is next: the
chart hub and day economy, with two thin sites to prove world-switching at scale
before there is content to lose.
