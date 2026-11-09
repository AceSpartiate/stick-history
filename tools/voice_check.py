#!/usr/bin/env python3
"""Listen to every recorded sentence with the local Whisper server and list the ones
that do not say what the script says - garbled, clipped, or a word Kokoro cannot read.

    python tools/voice_check.py <harvest.json> <report.md> [--below 0.75]

Whisper (large-v3, 127.0.0.1:9000) mishears names it has never met, so a low score is
a reason to listen, not proof of a fault. Read-only: it changes no file in the game.
"""
import argparse, difflib, json, os, re, sys, time
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from voice_build import fnv1a, OUT

NUM = {"1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six",
       "7": "seven", "8": "eight", "9": "nine", "10": "ten"}


def words(t):
    t = t.lower().replace("’", "'")
    t = re.sub(r"[^a-z0-9' ]+", " ", t)
    return [NUM.get(w, w) for w in t.split()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("harvest")
    ap.add_argument("report")
    ap.add_argument("--below", type=float, default=0.75)
    a = ap.parse_args()
    items = json.load(open(a.harvest, encoding="utf-8"))["chunks"]
    rows, n = [], 0
    for it in items:
        f = os.path.join(OUT, fnv1a(it["t"]) + ".ogg")
        if not os.path.exists(f):
            continue
        want = words(it["t"])
        if len(want) < 3:
            continue
        for _ in range(120):  # the server steps aside for games and other GPU work; wait it out
            with open(f, "rb") as fh:
                r = requests.post("http://127.0.0.1:9000/asr", params={"language": "en", "output": "txt"},
                                  files={"audio_file": (os.path.basename(f), fh, "audio/ogg")}, timeout=600)
            if r.ok and "retry later" not in r.text:
                break
            time.sleep(30)
        else:
            print("Whisper unavailable for an hour; stopping", flush=True)
            break
        got = words(r.text)
        score = difflib.SequenceMatcher(None, want, got).ratio()
        n += 1
        if score < a.below:
            rows.append((score, it["w"], it["t"], r.text.strip()))
        if n % 250 == 0:
            print("checked %d, %d below %.2f" % (n, len(rows), a.below), flush=True)
    rows.sort()
    with open(a.report, "w", encoding="utf-8") as fh:
        fh.write("# Narration check: %d sentences heard, %d below %.2f\n\n" % (n, len(rows), a.below))
        fh.write("| score | voice | script | Whisper heard |\n|---|---|---|---|\n")
        for s, w, t, h in rows:
            fh.write("| %.2f | %s | %s | %s |\n" % (s, w, t.replace("|", "/"), h.replace("|", "/").replace("\n", " ")))
    print("DONE %d heard, %d flagged -> %s" % (n, len(rows), a.report))


if __name__ == "__main__":
    main()
