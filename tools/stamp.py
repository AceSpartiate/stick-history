#!/usr/bin/env python3
"""Stamp a build id into index.html and version.txt, so a stale copy can tell.

GitHub Pages serves index.html with a cache lifetime. Without this, a tester can be
playing a build from before the last fix and reporting bugs that are already mended -
which happened once, and cost a round of confused debugging.

Run this before committing anything you intend to deploy:

    python tools/stamp.py

It writes the same value in two places. index.html gets it as `const BUILD="..."`,
which is baked into whatever copy the browser has cached; version.txt gets it as the
only thing in the file, and is fetched with cache:"no-store". If they disagree, the
page is out of date and reloads itself once.

The two MUST be written together, which is the whole reason this is a script and not
a habit.
"""
import io
import os
import re
import subprocess
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "index.html")
VER = os.path.join(ROOT, "version.txt")


def build_id():
    """A UTC minute, plus the short commit if git can tell us one.

    The timestamp alone would be enough to detect staleness; the commit makes the
    value tell a human which build they are looking at.
    """
    stamp = time.strftime("%Y%m%d-%H%M", time.gmtime())
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT, capture_output=True, text=True, timeout=10,
        )
        if sha.returncode == 0 and sha.stdout.strip():
            return stamp + "-" + sha.stdout.strip()
    except Exception:
        pass
    return stamp


def main():
    bid = build_id()
    s = io.open(SRC, encoding="utf-8").read()
    new, n = re.subn(r'const BUILD="[^"]*";', 'const BUILD="%s";' % bid, s, count=1)
    if n != 1:
        raise SystemExit('could not find `const BUILD="...";` in index.html - '
                         "the update check may have been renamed or removed")
    io.open(SRC, "w", encoding="utf-8", newline="").write(new)
    io.open(VER, "w", encoding="utf-8", newline="").write(bid + "\n")
    print("stamped build %s" % bid)
    print("  index.html  -> const BUILD")
    print("  version.txt -> %s" % bid)


if __name__ == "__main__":
    main()
