#!/usr/bin/env python3
"""Stamp a build id - a UTC minute - into index.html and version.txt, so a stale
copy can tell.

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
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "index.html")
VER = os.path.join(ROOT, "version.txt")


def build_id():
    """A UTC minute, and nothing else.

    IT USED TO APPEND THE SHORT COMMIT, AND IT WAS ALWAYS THE WRONG ONE. This runs
    before `git commit`, so `git rev-parse HEAD` can only report the PREVIOUS commit.
    Checked over eight consecutive commits: every single build was stamped with its
    parent. A student reporting "build ...-5a36a62" was naming code that build does not
    contain, which makes the first step of every bug report point at the wrong place.

    Moving it later does not help, and this is the part worth understanding: a commit's
    hash is a hash of its own content, so no committed file can contain its own commit
    hash. Stamping after the commit and amending re-hashes the commit and invalidates
    the stamp again. It is a fixed point that does not exist, so the honest move is to
    stop reaching for it.

    The timestamp alone does the job this value actually has - the page compares it with
    version.txt to notice it is stale - and it is never wrong. To map a build back to
    code, find the first commit at or after that UTC minute:

        git log --format='%h %cI %s' --date-order | sort -k2

    If a hash is ever wanted in here again, it must be the hash of the CONTENT (say of
    index.html before stamping), never of the commit, because that one is knowable.
    """
    return time.strftime("%Y%m%d-%H%M", time.gmtime())


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
