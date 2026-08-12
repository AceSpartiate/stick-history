# -*- coding: utf-8 -*-
"""Splice additional dialogue choices into index.html from a JSON draft.

WHY A TOOL AND NOT AN EDIT. The new conversation paths were written by several agents at
once, and having any of them edit an 19,000-line single file would have been a race with
no winner. They return DATA - a question, a reply, and the TITLE of the insight the beat
already grants - and this puts it in.

WHICH MEANS NOBODY WRITES AN INSIGHT BODY BUT THE ORIGINAL AUTHOR. A wise choice names its
insight by title; this copies the existing insight literal across, character for
character, from the choice already in the file. So an alternative route cannot drift from
the thing it is supposed to teach, cannot invent a new codex entry, and cannot inflate the
scrivener's target count - collectInsights keys on the title and dedupes.

  python tools/add_choices.py draft.json          # check only, prints what it would do
  python tools/add_choices.py draft.json --write   # do it

The draft is {"speakers":[{"npc":"sailor","draft":{"beats":[{"beat":0,"add":[...]}]}}]}
or a bare list of per-speaker objects; both shapes are accepted.
"""
import io, json, re, sys

SRC = "C:/Users/zachw/Desktop/stick-history/index.html"


def skip(src, j):
    """If a comment starts at j, return the index just past it; otherwise j.

    THIS IS NOT FUSSINESS. The first version of this scanner tracked strings but not
    comments, and the beats it was supposed to be splitting are documented with lines
    like "the one that puts two men's halves together" - so the apostrophe in men's
    opened a string that ran on until the next quote, three comments later, and every
    brace in between was counted on the wrong side. The parse silently walked off the
    end of the array. A scanner over this file has to know about comments because this
    file is more comment than code, and the comments have apostrophes in them.
    """
    if src.startswith("/*", j):
        e = src.find("*/", j + 2)
        return (len(src) if e < 0 else e + 2)
    if src.startswith("//", j):
        e = src.find("\n", j + 2)
        return (len(src) if e < 0 else e + 1)
    return j


def match(src, i):
    """i indexes an opening bracket; return the index of its partner."""
    depth, j, instr = 0, i, None
    while j < len(src):
        if not instr:
            k = skip(src, j)
            if k != j:
                j = k
                continue
        c = src[j]
        if instr:
            if c == "\\":
                j += 2
                continue
            if c == instr:
                instr = None
        elif c in "\"'":
            instr = c
        elif c in "[{(":
            depth += 1
        elif c in "]})":
            depth -= 1
            if depth == 0:
                return j
        j += 1
    raise ValueError("unbalanced at %d" % i)


def objects(src):
    """top-level {...} literals in an array body, with their spans"""
    out, depth, start, instr, j = [], 0, None, None, 0
    while j < len(src):
        if not instr:
            k = skip(src, j)
            if k != j:
                j = k
                continue
        c = src[j]
        if instr:
            if c == "\\":
                j += 2
                continue
            if c == instr:
                instr = None
        elif c in "\"'":
            instr = c
        elif c == "{":
            if depth == 0:
                start = j
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0 and start is not None:
                out.append((start, j + 1))
                start = None
        j += 1
    return out


def js_string(t):
    """A JS double-quoted literal, ASCII-only.

    Straight quotes inside a line are turned into the curly pair the rest of the file
    uses - open on the odd one, close on the even - because every spoken line in this
    game is wrapped in them and an agent writing plain " would otherwise be the only
    voice on the ship without them.
    """
    out, opening = [], True
    for ch in t:
        if ch == '"':
            out.append(u"\u201c" if opening else u"\u201d")
            opening = not opening
            continue
        out.append(ch)
    t = "".join(out)
    t = t.replace("\\", "\\\\")
    esc = []
    for ch in t:
        o = ord(ch)
        if ch == '"':
            esc.append('\\"')
        elif 32 <= o < 127:
            esc.append(ch)
        else:
            esc.append("\\u%04x" % o)
    return '"' + "".join(esc) + '"'


def insight_of(choice_src):
    """the verbatim `insight:{...}` literal inside a choice, or None"""
    m = re.search(r"\binsight:\s*\{", choice_src)
    if not m:
        return None
    i = choice_src.index("{", m.end() - 1)
    return choice_src[i:match(choice_src, i) + 1]


def title_of(ins_src):
    m = re.search(r'\bb:"((?:[^"\\]|\\.)*)"', ins_src or "")
    return m.group(1) if m else None


def load(path):
    d = json.load(io.open(path, encoding="utf-8"))
    rows = d.get("speakers", d) if isinstance(d, dict) else d
    out = []
    for r in rows:
        draft = r.get("draft", r)
        out.append((draft.get("npc") or r.get("npc"), draft.get("beats", [])))
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    write = "--write" in sys.argv
    drafts = load(sys.argv[1])
    s = io.open(SRC, encoding="utf-8").read()

    # locate every npc block once, newest offsets recomputed after each edit
    added = errors = 0
    report = []
    for npc_id, beats in drafts:
        for entry in sorted(beats, key=lambda e: -int(e["beat"])):
            bi = int(entry["beat"])
            # find the npc, then its beats[], then beat bi, then its choices[]
            m = re.search(r'\{id:"%s"' % re.escape(npc_id), s)
            if not m:
                report.append("FAIL  no npc %s" % npc_id)
                errors += 1
                continue
            npc_span = match(s, m.start())
            npc_src = s[m.start():npc_span + 1]
            bm = re.search(r"\bbeats:\s*\[", npc_src)
            b_open = npc_src.index("[", bm.end() - 1)
            b_body = npc_src[b_open + 1:match(npc_src, b_open)]
            spans = objects(b_body)
            if bi >= len(spans):
                report.append("FAIL  %s beat %d of %d" % (npc_id, bi, len(spans)))
                errors += 1
                continue
            bs, be = spans[bi]
            beat_src = b_body[bs:be]
            cm = re.search(r"\bchoices:\s*\[", beat_src)
            c_open = beat_src.index("[", cm.end() - 1)
            c_close = match(beat_src, c_open)
            c_body = beat_src[c_open + 1:c_close]
            existing = objects(c_body)
            # the insight literals this beat already grants, by title
            bank = {}
            for (a, b) in existing:
                ins = insight_of(c_body[a:b])
                t = title_of(ins)
                if t:
                    bank[t] = ins
            texts = [c_body[a:b] for (a, b) in existing]

            pieces = []
            for c in entry.get("add", []):
                t = (c.get("t") or "").strip()
                reply = (c.get("reply") or "").strip()
                if not t or not reply:
                    report.append("skip  %s b%d: empty t/reply" % (npc_id, bi))
                    continue
                if any(('t:"%s"' % t.replace('"', '')) in x for x in texts):
                    report.append("skip  %s b%d: duplicate t" % (npc_id, bi))
                    continue
                out = ["{t:" + js_string(t)]
                if c.get("wise"):
                    ref = (c.get("insightRef") or "").strip()
                    if ref not in bank:
                        report.append("FAIL  %s b%d: insightRef %r not granted by this beat "
                                      "(has: %s)" % (npc_id, bi, ref, ", ".join(bank) or "none"))
                        errors += 1
                        continue
                    out.append("wise:true")
                    out.append("ink:%d" % int(c.get("ink") or 8))
                elif c.get("fair"):
                    out.append("fair:true")
                    out.append("ink:%d" % int(c.get("ink") or 3))
                else:
                    out.append("wise:false")
                out.append("\n     reply:" + js_string(reply))
                if c.get("wise"):
                    out.append("\n     insight:" + bank[c["insightRef"].strip()])
                pieces.append("    " + ",".join(out) + "}")

            if not pieces:
                continue
            new_body = c_body.rstrip() + ",\n" + ",\n".join(pieces) + "\n   "
            new_beat = beat_src[:c_open + 1] + new_body + beat_src[c_close:]
            new_b_body = b_body[:bs] + new_beat + b_body[be:]
            new_npc = npc_src[:b_open + 1] + new_b_body + npc_src[match(npc_src, b_open):]
            s = s[:m.start()] + new_npc + s[npc_span + 1:]
            added += len(pieces)
            report.append("ok    %s beat %d: +%d choices" % (npc_id, bi, len(pieces)))

    for r in sorted(report):
        print(" ", r)
    print("\n%d choices to add, %d errors" % (added, errors))
    if errors:
        print("refusing to write while anything is wrong")
        return 1
    if write:
        io.open(SRC, "w", encoding="utf-8", newline="").write(s)
        print("written")
    else:
        print("(dry run - pass --write to apply)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
