#!/usr/bin/env python3
"""Record the game's narration ahead of time with Kokoro, so read-aloud works on every
device - including Android, where the browser has no speech engine at all.

    python tools/voice_build.py <harvest.json> [--jobs 5] [--limit N]

<harvest.json> (tools/voice_lines.json, made by tools/voice_harvest.js) is {"chunks":[{"t": text, "w": who}]}: every sentence the game can
speak, exactly as chunkForSpeech() cuts it, and who owns it ("narrator" or an npc id).
It is produced in the page (see the morning report, 2026-11-09). Each sentence becomes
assets/voice/<fnv1a32 of the text>.ogg, the same hash voiceKey() computes in the
game, and assets/voice/index.json lists the ids so the game asks only for files
that exist. Resumable: a file already there is skipped.

Kokoro-82M v1.0 (Apache-2.0) via sherpa-onnx, both borrowed from Texas
Civilization's runtime\\voice. CPU only, so no GPU lease is needed.
"""
import argparse, json, os, re, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "voice")
RT = r"C:\Users\zachw\Texas Civilization\runtime\voice"
TTS = os.path.join(RT, "bin", "sherpa-onnx-offline-tts.exe")
OPUS = os.path.join(RT, "bin", "opusenc.exe")
K = os.path.join(RT, "kokoro")

# Kokoro speaker ids: 24 bm_daniel, 25 bm_fable, 26 bm_george, 27 bm_lewis (British men).
# Four British male voices for seventeen speakers, so speed separates the ones that share.
VOICES = {
    "narrator": (26, 1.00),
    "sailor": (27, 0.92), "kendall": (27, 0.97), "helmsman": (27, 1.03), "cook": (27, 1.06), "sick": (27, 0.90),
    "clerk": (24, 1.00), "wingfield": (24, 0.93), "hunt": (24, 0.90), "cooper": (24, 1.04), "archer": (24, 1.06),
    "gent": (25, 1.04), "newport": (25, 0.95), "percy": (25, 1.00), "boy": (25, 1.12), "irons": (25, 0.98),
    "snore": (25, 0.90),
    # Chapter III (stand-ins until the character voices are recorded)
    "gosnold": (24, 0.97), "laydon": (27, 1.00), "laxon": (25, 0.93), "smith": (26, 1.06),
    # Chapter IV (stand-ins until voice_cast.py designs them)
    "studley": (26, 0.94), "ratcliffe": (27, 1.01), "martin": (25, 0.96),
    # Chapter V
    "read": (27, 0.94), "bargeman": (25, 1.02),
    # Chapter VI
    "scrivener": (24, 1.02), "todkill": (27, 0.98), "russell": (26, 0.96),
    # Chapter VII
    "spelman": (25, 1.10), "davis": (27, 1.03), "strachey": (24, 0.98), "gates": (26, 0.92), "digger": (25, 1.04),
}
FEMALE = (21, 1.0)  # bf_emma, for any speaker marked voice:"female"

# Pronunciation only: the key stays the original text. Respellings for names espeak
# has never heard; each is how the place is said locally today.
SAY = [(r"\bKecoughtan\b", "Kick-oh-tan"), (r"\bPaspahegh\b", "Pass-pa-hay"),
       (r"\bweroance(s?)\b", r"wero-ance\1"), (r"\bPowhatan\b", "Pow-a-tan")]


def fnv1a(s):
    h = 0x811C9DC5
    for b in s.encode("utf-8"):
        h ^= b
        h = (h * 0x01000193) & 0xFFFFFFFF
    return "%08x" % h


ROMAN = {"I": "one", "II": "two", "III": "three", "IV": "four", "V": "five", "VI": "six",
         "VII": "seven", "VIII": "eight", "IX": "nine", "X": "ten"}
KEEP_CAPS = {"STAAR", "OK"}


def say_form(t):
    """What Kokoro is given. Found by Whisper on 2026-11-09: espeak reads curly quotes
    and curly apostrophes as noise ("I umlaut a half"), says a full stop after a closing
    quote as "dot", and spells a word in capitals letter by letter ("SEE" -> "S. E.")."""
    t = t.replace("’", "'").replace("‘", "'").replace("“", "").replace("”", "")
    t = re.sub(r"\b(Chapter|Part|Act|Phase) (I{1,3}|IV|VI{0,3}|IX|X)\b",
               lambda m: m.group(1) + " " + ROMAN[m.group(2)], t)
    t = re.sub(r"\b[A-Z]{2,}\b", lambda m: m.group(0) if m.group(0) in KEEP_CAPS else m.group(0).lower(), t)
    t = re.sub(r"^\s*[,;:]\s*", "", t)  # a piece that starts mid-sentence starts on the word
    for a, b in SAY:
        t = re.sub(a, b, t)
    return t.strip()


def junk(t):
    """Strings the harvest finds that nobody ever hears: encoded data and identifiers."""
    return bool(re.search(r"\S{28,}", t) or re.search(r"\w_\w", t) or not re.search(r"[aeiouy]", t, re.I))


def one(item, npcs, redo=False):
    t, who = item["t"], item["w"]
    hid = fnv1a(t)
    dst = os.path.join(OUT, hid + ".ogg")
    if os.path.exists(dst) and not (redo and say_form(t) != t.strip()):
        return hid, "skip"
    sid, speed = VOICES.get(who, VOICES["narrator"])
    if npcs.get(who, {}).get("voice") == "female":
        sid, speed = FEMALE
    wav = os.path.join(tempfile.gettempdir(), "sh_voice_%s.wav" % hid)
    r = subprocess.run([TTS, "--kokoro-model=" + os.path.join(K, "model.onnx"),
                        "--kokoro-voices=" + os.path.join(K, "voices.bin"),
                        "--kokoro-tokens=" + os.path.join(K, "tokens.txt"),
                        "--kokoro-data-dir=" + os.path.join(K, "espeak-ng-data"),
                        "--kokoro-lang=en", "--num-threads=4", "--sid=%d" % sid,
                        "--kokoro-length-scale=%.3f" % (1 / speed),
                        "--output-filename=" + wav, say_form(t)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode or not os.path.exists(wav):
        return hid, "FAIL tts: " + (r.stderr or "")[-200:]
    r = subprocess.run([OPUS, "--quiet", "--bitrate", "20", "--speech", wav, dst],
                       capture_output=True, text=True)
    os.remove(wav)
    return hid, "ok" if r.returncode == 0 else "FAIL opus"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("harvest")
    ap.add_argument("--jobs", type=int, default=5)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--redo", action="store_true",
                    help="re-record every sentence whose spoken form say_form() changes")
    a = ap.parse_args()
    d = json.load(open(a.harvest, encoding="utf-8"))
    items, npcs = [c for c in d["chunks"] if not junk(c["t"])], d.get("npcs", {})
    if a.limit:
        items = items[:a.limit]
    os.makedirs(OUT, exist_ok=True)

    done = fail = 0
    with ThreadPoolExecutor(a.jobs) as ex:
        for hid, st in ex.map(lambda it: one(it, npcs, a.redo), items):
            if st.startswith("FAIL"):
                fail += 1
                print(hid, st, flush=True)
            else:
                done += 1
            if (done + fail) % 250 == 0:
                print("progress %d/%d, %d failed" % (done + fail, len(items), fail), flush=True)
    ids = sorted(f[:-4] for f in os.listdir(OUT) if f.endswith(".ogg"))
    json.dump({"v": 1, "ids": ids}, open(os.path.join(OUT, "index.json"), "w"), separators=(",", ":"))
    print("DONE %d ok, %d failed, %d files listed" % (done, fail, len(ids)))


if __name__ == "__main__":
    main()
