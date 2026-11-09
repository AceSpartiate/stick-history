#!/usr/bin/env python3
"""make_textures.py - ground DETAIL textures for Stick History, painted locally and judged by a local model.

    python tools/textures/make_textures.py [--only sand,grass] [--seeds 4] [--work <scratch dir>] [--no-paint]

--no-paint reprocesses the paintings already in --work and asks the model again (no GPU lease, no unload).

The game's look is vertex colour on low-poly form, and it stays that. What the ground lacks is grain: a beach is
one flat tan. A detail texture adds only that - a small tiling LUMINANCE map multiplied over the vertex colours,
mean ~0.82 (the game lifts the material by 1/0.82, so the average colour is unchanged and the palette still owns
the hue). One per ground type, 512 px JPEG, a few tens of KB.

  1. Z-Image Turbo (Apache-2.0; ComfyUI through the shared comfy.py queue) paints N top-down candidates.
  2. Each is made seamless (offset-and-blend), desaturated, and normalised to the detail range.
  3. qwen3.8:27b looks at each candidate tiled 2x2 and picks the one that tiles invisibly and reads as the
     material, or rejects all of them. Claude looks only at what it passes.
Output: assets/tex/<name>.jpg, previews and the model's verdicts in --work. 2026-11-09.
"""
import base64, io, json, os, sys, time, urllib.request
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, r'E:\VN-Tools\asset-toolkit')

TEXTURES = {
    'sand': 'dry pale beach sand with fine wind ripples and a few tiny shell fragments',
    'grass': 'short rough meadow grass with clover and small weeds, natural and uneven',
    'earth': 'trampled bare brown earth with small pebbles, footprints and bits of dry grass',
    'forest': 'pine forest floor covered in brown pine needles, twigs and a few small cones',
    'marsh': 'wet muddy marsh ground with tufts of coarse reed grass and small puddles',
}
STYLE = ('seamless tileable texture, photographed straight down from directly above, flat even overcast light, '
         'no shadows, no horizon, no objects, no text, uniform detail across the whole frame, high detail')
MEAN, SPREAD = 0.82, 0.10


def seamless(a):
    """Offset-and-blend: the rolled copy is continuous across the tile edges, the original across the middle."""
    h, w = a.shape[:2]
    r = np.roll(np.roll(a, h // 2, 0), w // 2, 1)
    y = np.minimum(np.arange(h), h - 1 - np.arange(h)) / (h / 2)
    x = np.minimum(np.arange(w), w - 1 - np.arange(w)) / (w / 2)
    m = np.clip(np.minimum.outer(y, x) * 1.6, 0, 1)
    m = (m * m * (3 - 2 * m))[..., None] if a.ndim == 3 else m * m * (3 - 2 * m)
    return a * m + r * (1 - m)


def detail(img):
    a = np.asarray(img.convert('RGB').resize((1024, 1024), Image.LANCZOS), dtype=np.float32) / 255
    a = seamless(a)
    lum = a @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    # High-pass: brightness that drifts across the painting tiles as a checkerboard (found by eye on 2026-11-09 in
    # grass that the model passed). Subtract a heavily smoothed copy so only grain is left.
    low = np.asarray(Image.fromarray(lum).resize((12, 12), Image.BILINEAR).resize(lum.shape[::-1], Image.BICUBIC))
    lum = lum - low
    # and clamp the outliers: one dark pine cone repeats as a grid of dots every tile
    z = np.clip((lum - lum.mean()) / (lum.std() + 1e-6), -2.0, 2.0)
    lum = z / (z.std() + 1e-6) * SPREAD + MEAN
    lum = np.clip(lum, 0.45, 1.0)
    return Image.fromarray((lum * 255).astype(np.uint8), 'L').resize((512, 512), Image.LANCZOS)


def ask_vision(prompt, images):
    body = {'model': 'qwen3.8:27b', 'stream': False, 'think': False, 'keep_alive': '2h',
            'options': {'temperature': 0.1, 'num_ctx': 16384},
            'messages': [{'role': 'user', 'content': prompt, 'images': images}],
            'format': {'type': 'object', 'properties': {'best': {'type': 'integer'}, 'ok': {'type': 'boolean'},
                                                        'why': {'type': 'string'}}, 'required': ['best', 'ok', 'why']}}
    req = urllib.request.Request('http://127.0.0.1:11434/api/chat', data=json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json'})
    return json.loads(json.loads(urllib.request.urlopen(req, timeout=1800).read())['message']['content'])


def tiled(im):
    w, h = im.size
    t = Image.new('L', (w * 2, h * 2))
    for i in range(2):
        for j in range(2):
            t.paste(im, (i * w, j * h))
    return t.resize((768, 768))


def main():
    argv = sys.argv[1:]
    opt = lambda k, d=None: argv[argv.index(k) + 1] if k in argv else d
    only = set((opt('--only') or '').split(',')) - {''}
    seeds = int(opt('--seeds', 4))
    work = opt('--work', os.path.join(HERE, '_work'))
    os.makedirs(work, exist_ok=True)
    out = os.path.join(ROOT, 'assets', 'tex')
    os.makedirs(out, exist_ok=True)
    names = [n for n in TEXTURES if not only or n in only]

    if '--no-paint' in argv:
        return judge(names, seeds, work, out)
    import comfy
    from workflows import z_image
    # the model sits on both cards; painting needs one of them
    try:
        urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:11434/api/generate',
                               data=json.dumps({'model': 'qwen3.8:27b', 'keep_alive': 0}).encode(),
                               headers={'Content-Type': 'application/json'}), timeout=60).read()
    except Exception:
        pass
    with comfy.Comfy() as c:
        for n in names:
            for s in range(seeds):
                dst = os.path.join(work, f'{n}_{s}_raw.png')
                if os.path.exists(dst):
                    continue
                got = c.run(z_image(f'{TEXTURES[n]}, {STYLE}', width=1024, height=1024, seed=1000 + s,
                                    prefix=f'sh_tex_{n}'), os.path.join(work, '_raw'))
                Image.open(got[0]).convert('RGB').save(dst)
                print(time.strftime('%H:%M:%S'), 'painted', n, s, flush=True)
        try:
            comfy._req('/free', {'unload_models': True, 'free_memory': True})
        except Exception:
            pass

    judge(names, seeds, work, out)


def judge(names, seeds, work, out):
    verdicts = {}
    for n in names:
        cands, imgs = [], []
        for s in range(seeds):
            d = detail(Image.open(os.path.join(work, f'{n}_{s}_raw.png')))
            d.save(os.path.join(work, f'{n}_{s}_detail.png'))
            t = tiled(d)
            t.save(os.path.join(work, f'{n}_{s}_tiled.jpg'), quality=85)
            b = io.BytesIO()
            t.convert('RGB').save(b, 'JPEG', quality=85)
            imgs.append(base64.b64encode(b.getvalue()).decode())
            cands.append(d)
        v = ask_vision(
            f'These {seeds} greyscale images (numbered 0 to {seeds - 1} in the order given) are candidate ground '
            f'textures for a game, each shown TILED 2x2 so you can see whether the tile edges show. The material is: '
            f'{TEXTURES[n]}. Pick the best one: the repeat must be invisible (no visible seam lines or a cross '
            f'through the middle, no checkerboard of lighter and darker squares, no grid of the same dark spot repeating), it must read as that material seen '
            f'from above, with even detail and no objects, text or strong shadows. ok=false if none is acceptable.',
            imgs)
        verdicts[n] = v
        print(time.strftime('%H:%M:%S'), n, v, flush=True)
        if v.get('ok') and 0 <= v.get('best', -1) < seeds:
            cands[v['best']].save(os.path.join(out, f'{n}.jpg'), quality=82)
    json.dump(verdicts, open(os.path.join(work, 'verdicts.json'), 'w'), indent=1)
    print('DONE', {k: (v['ok'], v['best']) for k, v in verdicts.items()})


if __name__ == '__main__':
    main()
