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

1. Create an **empty** public repo — no README, no .gitignore, or the first
   push is rejected as non-fast-forward
2. `git remote add origin https://github.com/<you>/<repo>.git`
   then `git push -u origin main`
3. **Settings → Pages → Deploy from a branch →** `main` / `/root`
4. Open `https://<you>.github.io/<repo>/`

`index.html` is at the repository root, which is what `/root` above means. Pages
needs the repo public on a free account — and that publishes `CLAUDE.md` and
`docs/` along with the game.

Hosting matters for more than convenience: `localStorage` is unreliable over
`file://`, so save-and-resume only works properly on a served page. Students on
different machines carry progress with the **Muster Code** in the pause menu.

## Check before committing

```
python3 tools/check.py
```

On Windows that is `python tools/check.py`. Check 1 shells out to `node --check`
and is the only step with an external dependency; without Node on PATH it skips
and the other seven still run.

Eight checks, each corresponding to a bug that reached the player at least once —
unwired actions, unregistered modals, unguarded element reads, undefined calls,
over-long cutscenes, and accidental image assets.

You do not have to remember to run it. `.githooks/pre-commit` runs it for you and
refuses the commit if anything fails. It is tracked, so it travels with the repo,
but git has to be pointed at it **once per clone**:

```
git config core.hooksPath .githooks
```

`git commit --no-verify` gets past a failure on purpose.

## Read first

- `CLAUDE.md` — conventions, invariants, and the bug classes that recurred
- `docs/BUILD_PLAN.md` — status, settled decisions, phase order, open questions
- `docs/CHAPTER_2_DESIGN.md` — the original Chapter II design (§1–8 still stand)

## Where things stand

Phases 0, 1, 2 and 2.5 complete. Chapter I (the bay mouth, dawn 26 April 1607)
and Chapter II (Cape Henry, that afternoon) are playable. **Phase 3** is next: the
chart hub and day economy, with two thin sites to prove world-switching at scale
before there is content to lose.
