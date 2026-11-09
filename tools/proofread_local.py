#!/usr/bin/env python3
"""Proofread the game's prose with a LOCAL model, for typos only, and write a report.

    python tools/proofread_local.py <report.md> [--model qwen3.8:27b] [--batch 25]

Finds every double-quoted string in index.html with six or more words, asks the model
for clear mechanical errors only, and also runs two free checks (doubled words,
unbalanced curly quotes). It edits nothing: the report is read by a person, because a
small model will propose "fixes" to period English, and the record is kept as the
sources wrote it. Ollama is called directly (127.0.0.1:11434), after the shared
toolkit's wait_for_4060ti(), per LOCAL_AI.md.
"""
import argparse, json, re, sys, urllib.request

sys.path.insert(0, r"E:\VN-Tools\asset-toolkit")
try:
    import comfy
except Exception:
    comfy = None

ROOT = __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__)))
PROMPT = """You are proofreading prose from an educational history game set in 1607 Virginia.
Report ONLY clear mechanical errors a careful editor would fix without discussion:
- a misspelled modern English word (not a name, not a period spelling)
- a word repeated by accident ("the the")
- a missing or extra word that leaves a sentence broken
- the wrong common word ("their" for "there", "it's" for "its")
Do NOT report: British spelling; archaic or 17th-century spelling and capitals, especially
inside quotations from period sources; style, tone, word choice or punctuation preferences;
historical claims; sentence fragments used for effect; names.
When unsure, do not report it. Most items have no error; an empty list is the normal answer.

Items:
"""
SCHEMA = {"type": "object", "properties": {"errors": {"type": "array", "items": {
    "type": "object", "properties": {"n": {"type": "integer"}, "wrong": {"type": "string"},
                                      "right": {"type": "string"}, "why": {"type": "string"}},
    "required": ["n", "wrong", "right", "why"]}}}, "required": ["errors"]}


def strings(src):
    out, seen = [], set()
    for m in re.finditer(r'"((?:[^"\\\n]|\\.){30,})"', src):
        raw = m.group(1)
        try:
            s = json.loads('"' + raw + '"')
        except Exception:
            continue
        s = re.sub(r"<[^>]*>", " ", s)
        s = re.sub(r"\s+", " ", s).strip()
        if len(s.split()) < 6 or s in seen or re.search(r"[{};]|=>|function\(|px\b", s):
            continue
        seen.add(s)
        out.append((src.count("\n", 0, m.start()) + 1, s))
    return out


def ask(model, batch):
    body = PROMPT + "\n".join("%d. %s" % (i + 1, s) for i, (_, s) in enumerate(batch))
    req = {"model": model, "stream": False, "think": False, "format": SCHEMA,
           "options": {"temperature": 0, "num_ctx": 16384},
           "messages": [{"role": "user", "content": body}]}
    r = urllib.request.urlopen(urllib.request.Request(
        "http://127.0.0.1:11434/api/chat", json.dumps(req).encode(),
        {"Content-Type": "application/json"}), timeout=900)
    return json.loads(json.loads(r.read())["message"]["content"]).get("errors", [])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("report")
    ap.add_argument("--model", default="qwen3.8:27b")
    ap.add_argument("--batch", type=int, default=25)
    a = ap.parse_args()
    src = open(ROOT + "/index.html", encoding="utf-8").read()
    items = strings(src)
    rows = []
    for ln, s in items:  # free checks first
        for m in re.finditer(r"\b(\w+) \1\b", s, re.I):
            if m.group(1).lower() not in {"had", "that", "very", "no", "is"}:
                rows.append((ln, "doubled word", m.group(0), m.group(1), s))
        if s.count("\u201c") != s.count("\u201d") and len(s) < 400:
            rows.append((ln, "unbalanced quotes", "\u201c%d \u201d%d" % (s.count("\u201c"), s.count("\u201d")), "", s))
    if comfy and hasattr(comfy, "wait_for_4060ti"):
        comfy.wait_for_4060ti()
    for i in range(0, len(items), a.batch):
        b = items[i:i + a.batch]
        try:
            errs = ask(a.model, b)
        except Exception as e:
            print("batch %d failed: %s" % (i, e), flush=True)
            continue
        for e in errs:
            n = e.get("n", 0) - 1
            if 0 <= n < len(b) and e.get("wrong") and e["wrong"] in b[n][1] and e["wrong"] != e.get("right"):
                rows.append((b[n][0], "model: " + e.get("why", ""), e["wrong"], e.get("right", ""), b[n][1]))
        print("batch %d/%d, %d flagged so far" % (i // a.batch + 1, -(-len(items) // a.batch), len(rows)), flush=True)
    rows.sort()
    with open(a.report, "w", encoding="utf-8") as f:
        f.write("# Proofread report (%s, %d strings)\n\nNothing here has been applied.\n\n" % (a.model, len(items)))
        f.write("| line | kind | found | suggested | context |\n|---|---|---|---|---|\n")
        for ln, kind, wrong, right, ctx in rows:
            c = ctx if len(ctx) < 160 else ctx[max(0, ctx.find(wrong) - 70):ctx.find(wrong) + 90]
            f.write("| %d | %s | %s | %s | %s |\n" % (ln, kind.replace("|", "/"), wrong.replace("|", "/"),
                                                     right.replace("|", "/"), c.replace("|", "/")))
    print("DONE %d strings, %d flagged -> %s" % (len(items), len(rows), a.report))


if __name__ == "__main__":
    main()
