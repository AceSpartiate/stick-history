#!/usr/bin/env python3
"""voice_cast.py - give every character in the game his own voice. The narrator stays Kokoro (voice_build.py).

    python E:\\VN-Tools\\asset-toolkit\\gpu_job.py -- E:\\VN-Tools\\qwen3-tts\\.venv\\Scripts\\python.exe ^
        tools\\voice_cast.py design|clone [--who a,b] [--limit N]
    (run it with GPU_EITHER=1 so it takes whichever card is free; LOCAL_AI.md rule 10)

design: Qwen3-TTS 1.7B VoiceDesign (Apache-2.0) speaks one reference line per character from a written description
        of the man (CAST below) -> tools/voice_cast/<who>.wav, and a cast reel to listen to, cast_reel.wav.
clone:  Qwen3-TTS 1.7B Base (Apache-2.0) clones each reference for every line that character speaks in
        tools/voice_lines.json -> assets/voice/<fnv1a of the text>.ogg, replacing the Kokoro stand-in. Designing
        once and cloning keeps a voice the same from line to line; VoiceDesign alone re-invents it every call.
Resumable: tools/voice_cast/done.json maps each file to who spoke it and the text it was made from.
Then run tools/voice_check.py (Whisper) on the result. 2026-11-25.
"""
import json, os, subprocess, sys, tempfile, time
import numpy as np
import soundfile as sf
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from voice_build import fnv1a, say_form, junk, OUT, OPUS  # noqa: E402

CAST_DIR = os.path.join(HERE, 'voice_cast')
DESIGN = r'F:\AI\tts\Qwen3-TTS-12Hz-1.7B-VoiceDesign'
BASE = r'F:\AI\tts\Qwen3-TTS-12Hz-1.7B-Base'
ENG = 'an English accent of the early 1600s, not American'
# Who each man is, as far as the record lets us say, and how he should sound. All speak English English.
CAST = {
    'wingfield': f"An English gentleman in his late fifties, President of a colonial council: stiff, formal and proud, "
                 f"measured and a little pompous, a dry upper-class voice, {ENG}.",
    'kendall': f"An English soldier in his thirties, a captain: clipped, hard and gruff, short sentences, a low firm "
               f"voice used to giving orders, {ENG}.",
    'gosnold': f"An English sea captain of about thirty-five: warm, steady authority, confident and plain-spoken, a "
               f"clear medium voice, {ENG}.",
    'smith': f"A young English soldier of twenty-seven from Lincolnshire: brash, quick and sure of himself, "
             f"energetic, a little impatient, a medium-high voice with a country edge, {ENG}.",
    'hunt': f"An English clergyman in his late thirties: gentle, calm and warm, a soft and patient preacher's voice, "
            f"{ENG}.",
    'laydon': f"A young English labourer in his twenties from the country: plain, honest and tired, a rough rural "
              f"accent, a medium voice, {ENG}.",
    'laxon': f"An English carpenter in his thirties: practical, steady and dry-humoured, a Midlands working man's "
             f"voice, medium-low, {ENG}.",
    'newport': f"An English sea captain in his late forties, master of a fleet: commanding and booming, a deep "
               f"weathered voice that carries across a deck, {ENG}.",
    'percy': f"A young English aristocrat of twenty-six, a nobleman's son: refined, soft-spoken and precise, a light "
             f"cultured voice, {ENG}.",
    'archer': f"An English gentleman of about thirty, trained in the law: articulate, sharp and quick, a crisp "
              f"medium voice, {ENG}.",
    'clerk': f"An English company clerk in his forties: precise, dry and a little nasal, careful with every word, "
             f"{ENG}.",
    'sailor': f"An old English seaman in his fifties from the West Country: gravelly, weathered and rough, slow and "
              f"knowing, a West Country burr, {ENG}.",
    'gent': f"A young English gentleman in his twenties seeking his fortune: eager, posh and a little arrogant, a "
            f"bright upper-class voice, {ENG}.",
    'cook': f"An English ship's cook in his forties: hoarse and grumbling, a rough working voice, {ENG}.",
    'boy': f"An English ship's boy of about twelve: a young boy's high clear voice, quick and cheeky, {ENG}.",
    'snore': f"A sleepy English sailor woken from sleep: mumbling, slow and drowsy, low and rough, {ENG}.",
    'sick': f"A seasick young English gentleman: weak, queasy and miserable, posh but faint, {ENG}.",
    'cooper': f"An English cooper in his fifties who mends barrels: grumpy, gruff and impatient, a rough craftsman's "
              f"voice, {ENG}.",
    'irons': f"An English prisoner held in chains below decks: hoarse, low, desperate and bitter, {ENG}.",
    'helmsman': f"A middle-aged English seaman at the helm: steady, terse and calm, a plain working voice, {ENG}.",
    # Chapter IV. Their ages are not recorded; these are only what their parts call for.
    'studley': f"An English merchant clerk keeping a colony's store: careful, anxious and tired, counting every "
               f"measure, a quiet precise middle voice, {ENG}.",
    'ratcliffe': f"An English sea captain of the council, sick and resentful: bitter, aggrieved and blustering, "
                 f"a harsh middle-aged voice, {ENG}.",
    'martin': f"An English gentleman of the council, a father whose son is sick: grieving and angry, a strained "
              f"older voice, {ENG}.",
}
REEL_GAP = 0.6


def lines_by_who():
    d = json.load(open(os.path.join(HERE, 'voice_lines.json'), encoding='utf-8'))
    out = {}
    for c in d['chunks']:
        if c['w'] in CAST and not junk(c['t']):
            out.setdefault(c['w'], []).append(c['t'])
    return out


def ref_line(lines):
    """The reference: a full sentence of his own, 12-30 words, so the clone hears him at a natural length."""
    good = [t for t in lines if 12 <= len(t.split()) <= 30 and t.strip()[-1:] in '.!?"\u201d']
    return say_form(sorted(good or lines, key=lambda t: abs(len(t.split()) - 20))[0])


def design(who_only, limit):
    from qwen_tts import Qwen3TTSModel
    os.makedirs(CAST_DIR, exist_ok=True)
    m = Qwen3TTSModel.from_pretrained(DESIGN, device_map='cuda:0', dtype=torch.bfloat16, attn_implementation='sdpa')
    by = lines_by_who()
    refs, reel, sr0 = {}, [], None
    for who, desc in CAST.items():
        if who_only and who not in who_only or who not in by:
            continue
        text = ref_line(by[who])
        torch.manual_seed(1607)
        wavs, sr = m.generate_voice_design(text=text, instruct=desc, language='English')
        sf.write(os.path.join(CAST_DIR, who + '.wav'), wavs[0], sr)
        refs[who] = {'text': text, 'desc': desc}
        reel += [wavs[0], np.zeros(int(sr * REEL_GAP), dtype=wavs[0].dtype)]
        sr0 = sr
        print(time.strftime('%H:%M:%S'), 'designed', who, f'{len(wavs[0]) / sr:.1f}s', flush=True)
    old = {}
    p = os.path.join(CAST_DIR, 'refs.json')
    if os.path.exists(p):
        old = json.load(open(p, encoding='utf-8'))
    old.update(refs)
    json.dump(old, open(p, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    if reel:
        sf.write(os.path.join(CAST_DIR, 'cast_reel.wav'), np.concatenate(reel), sr0)
    print('DONE design', len(refs))


def clone(who_only, limit):
    from qwen_tts import Qwen3TTSModel
    refs = json.load(open(os.path.join(CAST_DIR, 'refs.json'), encoding='utf-8'))
    donep = os.path.join(CAST_DIR, 'done.json')
    done = json.load(open(donep, encoding='utf-8')) if os.path.exists(donep) else {}
    m = Qwen3TTSModel.from_pretrained(BASE, device_map='cuda:0', dtype=torch.bfloat16, attn_implementation='sdpa')
    by = lines_by_who()
    n = 0
    for who, lines in by.items():
        if who_only and who not in who_only or who not in refs:
            continue
        prompt = m.create_voice_clone_prompt(ref_audio=os.path.join(CAST_DIR, who + '.wav'), ref_text=refs[who]['text'])
        for t in lines:
            hid = fnv1a(t)
            if done.get(hid, {}).get('t') == t and done[hid].get('w') == who:
                continue
            torch.manual_seed(1607)
            wavs, sr = m.generate_voice_clone(text=say_form(t), language='English', voice_clone_prompt=prompt)
            wav = os.path.join(tempfile.gettempdir(), f'sh_cast_{hid}.wav')
            sf.write(wav, wavs[0], sr)
            r = subprocess.run([OPUS, '--quiet', '--bitrate', '20', '--speech', wav, os.path.join(OUT, hid + '.ogg')],
                               capture_output=True, text=True)
            os.remove(wav)
            if r.returncode:
                print('FAIL opus', who, hid, flush=True)
                continue
            done[hid] = {'w': who, 't': t}
            n += 1
            if n % 25 == 0:
                json.dump(done, open(donep, 'w', encoding='utf-8'), ensure_ascii=False)
                print(time.strftime('%H:%M:%S'), 'cloned', n, 'latest', who, flush=True)
            if limit and n >= limit:
                break
        if limit and n >= limit:
            break
    json.dump(done, open(donep, 'w', encoding='utf-8'), ensure_ascii=False)
    ids = sorted(f[:-4] for f in os.listdir(OUT) if f.endswith('.ogg'))
    json.dump({'v': 1, 'ids': ids}, open(os.path.join(OUT, 'index.json'), 'w'), separators=(',', ':'))
    print('DONE clone', n, 'lines;', len(ids), 'files listed')


if __name__ == '__main__':
    argv = sys.argv[1:]
    opt = lambda k: argv[argv.index(k) + 1] if k in argv else None
    who = set((opt('--who') or '').split(',')) - {''}
    lim = int(opt('--limit') or 0)
    {'design': design, 'clone': clone}[argv[0]](who, lim)
