#!/usr/bin/env python3
"""muster_draft.py - a local model drafts a chapter's muster (assessment) bank from the checked record; free
mechanical checks reject malformed items; Claude then reads every surviving item against the record.

    python tools/muster_draft.py <record.md> <design.md> <out.json> [--n 28] [--model qwen3.8:27b]

The model sees ONLY the record (and the chapter's design, for what the player does), plus three Chapter II items
as the house style. Every item must say which line of the record answers it ("src"), so the check against the
record is a lookup, not a hunt. Ollama directly (127.0.0.1:11434), after the toolkit's wait_for_4060ti(), per
LOCAL_AI.md. 2026-11-25.
"""
import json, re, sys, time, urllib.request

sys.path.insert(0, r'E:\VN-Tools\asset-toolkit')
try:
    import comfy
except Exception:
    comfy = None

STYLE = [
    {"stim": "The ground at Archer's Hope was black and the timber stood sixty feet and straight. Half the company "
             "would have settled there.",
     "q": "Good ground was NOT enough to settle Archer's Hope chiefly because -",
     "o": ["the water was too shoal for a ship to lie against the bank",
           "the Powhatan had already built a town on the site",
           "it lay too close to the open sea to be defended",
           "the timber there was unsuitable for building"], "a": 0},
    {"stim": "The names of the council were sealed in a box in London and read out at Cape Henry. The men aboard did "
             "not choose them, and did not know them until that hour.",
     "q": "This arrangement shows that authority in the colony rested on -",
     "o": ["the Company's decision in London, not on the colonists' consent",
           "an election held among the colonists at sea",
           "seniority, with the oldest man taking command",
           "the ship's master, who commanded ashore as well as afloat"], "a": 0},
    {"stim": "The Powhatan farmed a great deal of the better ground along the river. They had not settled this island.",
     "q": "A careful historian would treat the empty island as -",
     "o": ["evidence about the land's quality, since people who knew it had chosen not to use it",
           "proof that the region was almost entirely uninhabited",
           "a sign the Powhatan were unable to clear heavy timber",
           "unconnected to whether the site would support a settlement"], "a": 0},
]

PROMPT = """You are writing assessment questions for a history game played by 6th-8th graders in Texas. The chapter is
Jamestown, 14 May - 15 June 1607: building the first fort, the President's orders, the Paspahegh, the attack of 26 May,
and the triangle fort finished on 15 June.

THE RECORD (checked against the primary sources; this is the ONLY thing you may assert as fact):
<<<
{record}
>>>

WHAT THE PLAYER DOES in this chapter (so questions can ask about decisions they faced):
<<<
{design}
>>>

Write {n} multiple-choice items as a JSON object {{"items":[...]}}. Each item:
- "stim": a short stimulus (1-3 sentences) giving the facts the question needs, drawn ONLY from the record. Quote the
  sources' own words where it helps, with the writer's name.
- "q": the question, ending in a dash or a question mark. Ask about cause, evidence, significance, or what a careful
  historian can conclude - not trivia. Put the key word in CAPITALS when it is MOST / BEST / NOT / chiefly.
- "o": exactly four options; the FIRST is correct; the other three are plausible to a student who skimmed, wrong for a
  reason the record shows, and about the same length as the correct one. No "all of the above".
- "a": 0
- "src": the exact phrase from the record that makes option 0 right.
Never repeat the question's own words in an option. Where the sources disagree (the 26 May numbers), ask what the
disagreement means, never for one number as if it were settled. Use period words as the sources do; do not modernise
them. Spread the items over: the work and who did it, the President's order and rank, the Paspahegh visits, the attack,
why the accounts differ, and the fort that followed.

House style (three items from another chapter):
{style}"""

SCHEMA = {"type": "object", "properties": {"items": {"type": "array", "items": {
    "type": "object", "properties": {"stim": {"type": "string"}, "q": {"type": "string"},
                                     "o": {"type": "array", "items": {"type": "string"}},
                                     "a": {"type": "integer"}, "src": {"type": "string"}},
    "required": ["stim", "q", "o", "a", "src"]}}}, "required": ["items"]}


def problems(it, record):
    p = []
    if len(it['o']) != 4:
        p.append('needs exactly four options')
    if it['a'] != 0:
        p.append('a must be 0')
    if len(set(o.strip().lower() for o in it['o'])) < len(it['o']):
        p.append('duplicate options')
    qw = set(re.findall(r'[a-z]{5,}', it['q'].lower()))
    for o in it['o']:
        if len(qw & set(re.findall(r'[a-z]{5,}', o.lower()))) >= 3:
            p.append('an option repeats the question')
            break
    L = [len(o) for o in it['o']]
    if L[0] > 1.8 * (sum(L[1:]) / 3):
        p.append('the correct option is much longer than the others')
    src = re.sub(r'\s+', ' ', it.get('src', '')).strip().strip('"\u201c\u201d').lower()
    if len(src) < 8 or src[:40] not in re.sub(r'\s+', ' ', record).lower():
        p.append('src is not a phrase from the record')
    return p


def ask(model, prompt):
    body = {'model': model, 'stream': False, 'think': False, 'keep_alive': '30m', 'format': SCHEMA,
            'options': {'temperature': 0.4, 'num_ctx': 32768},
            'messages': [{'role': 'user', 'content': prompt}]}
    for k in range(60):
        try:
            req = urllib.request.Request('http://127.0.0.1:11434/api/chat', data=json.dumps(body).encode(),
                                         headers={'Content-Type': 'application/json'})
            return json.loads(json.loads(urllib.request.urlopen(req, timeout=3600).read())['message']['content'])
        except (OSError, ConnectionError) as e:          # the arbiter restarts Ollama on a game or Parsec switch
            print('retry', k, e, flush=True)
            time.sleep(30)
    raise SystemExit('Ollama unreachable')


def main():
    a = sys.argv[1:]
    opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    record, design, out = open(a[0], encoding='utf-8').read(), open(a[1], encoding='utf-8').read(), a[2]
    n, model = int(opt('--n', 28)), opt('--model', 'qwen3.8:27b')
    if comfy and hasattr(comfy, 'wait_for_4060ti'):
        comfy.wait_for_4060ti()
    got = ask(model, PROMPT.format(record=record, design=design, n=n, style=json.dumps(STYLE, indent=1,
                                                                                     ensure_ascii=False)))
    keep, drop = [], []
    for it in got.get('items', []):
        pr = problems(it, record)
        (drop if pr else keep).append(dict(it, problems=pr) if pr else it)
    json.dump({'keep': keep, 'drop': drop}, open(out, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print(f'DONE {len(keep)} kept, {len(drop)} dropped by the checks -> {out}')


if __name__ == '__main__':
    main()
