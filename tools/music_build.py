"""Stick History music (music, 27 Nov): one quiet loop per mood, made with ACE-Step 1.5 XL SFT.

Method and settings are the ones proven on MGA News (LOCAL_AI.md, Evidence log, 2026-11-15): ComfyUI's template
audio_ace_step1_5_xl_sft.json, 50 steps, cfg 7, AuraFlow shift 3, a rich prose caption naming the instruments, the
players and the room, and "no synthesizers". The turbo model was rejected by the owner as "all synth".

Licences (read 2026-11-26): ACE-Step 1.5 / XL SFT weights MIT (huggingface.co/ACE-Step/acestep-v15-xl-sft,
huggingface.co/ACE-Step/Ace-Step1.5); Comfy-Org repack Apache-2.0 (huggingface.co/Comfy-Org/ace_step_1.5_ComfyUI_files);
text encoders built on Qwen3-1.7B and Qwen3-Embedding-0.6B, Apache-2.0. Generated music: "can be used commercially".

English music of about 1600 only: lute, viols, recorder, cittern, tabor and pipe. No "Native American" music: none
survives that we could honestly use, and invented drums would be the curated fake history this project refuses.

  python tools/music_build.py [cue ...]     raw takes -> RAW/<cue>-s<seed>.flac (outside the repo)
  python tools/music_build.py --encode      loop + level + Opus -> assets/music/<cue>.ogg
GPU work goes through E:\\VN-Tools\\asset-toolkit\\comfy.py's lease; this never starts its own ComfyUI.
"""
import glob, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.environ.get("MUSIC_RAW", r"E:\VN-Tools\asset-toolkit\_out\stickhistory_music")
OUT = os.path.join(ROOT, "assets", "music")

ROOM = (" It is played by a small English consort of about 1600 on period acoustic instruments, recorded live and close in "
        "a quiet wood-panelled hall, soft and unhurried, background music for a history game. Purely instrumental: "
        "there is no singing and there are no words. There are no synthesizers, no electronic sounds, no drum kit, "
        "no piano, no orchestra and no modern instruments anywhere.")
LOOP = "[Instrumental]\n[Instrumental]\n[Instrumental]\n[Instrumental]"
SECS = 84   # generated length; the encoder folds the last 4 s over the first, leaving an 80 s seamless loop

# cue: caption, section notes, key, bpm, time signature, seeds (first is used; the second is the one retry)
CUES = {
 "title": ("A gentle, stately English pavan in the style of John Dowland and Anthony Holborne. A lute plays a noble, "
           "slightly wistful melody, a consort of three viols (treble, tenor and bass viol) bows warm sustained harmony "
           "beneath it, and an alto recorder answers the lute's phrases. Hopeful and dignified, at an even walking pace."
           + ROOM, LOOP, "D minor", 76, "4", (11, 12)),
 "voyage": ("A lilting English sea-going tune in the manner of a galliard, played on a long voyage. A cittern and a lute "
            "pick out a rolling, rocking rhythm like a ship on long swells, a bass viol plays a slow steady line, and a "
            "wooden recorder sings a simple, homesick melody over them. Patient, open and a little uncertain."
            + ROOM, LOOP, "A minor", 92, "3", (21, 22)),
 "fort": ("A busy, purposeful English country dance tune for men at work building a timber fort. A pipe and tabor play "
          "a bright tune over a light, steady tabor beat, a cittern strums chords, and a tenor viol and bass viol keep "
          "the harmony. Hopeful but watchful, with a sense of hard work under a hot sun."
          + ROOM, LOOP, "D major", 100, "4", (31, 32)),
 "sickness": ("A slow, melancholy English lute fantasia, music for a summer of fever and a hard winter. A solo lute plays "
              "quiet, searching lines with long pauses, and a bass viol holds soft, low, mournful notes under it. Grieving "
              "and still, very sparse, with plenty of silence between phrases."
              + ROOM, LOOP, "E minor", 60, "4", (41, 42)),
 "president": ("A firm, confident English almain, music for a hard-driving leader keeping order. A viol consort of treble, "
               "tenor and bass viols plays a strong, measured tune with dotted rhythms, a tabor taps a steady march pulse, "
               "and a lute and a recorder double the melody. Resolute and disciplined rather than cheerful."
               + ROOM, LOOP, "G minor", 96, "4", (51, 52)),
 "starving": ("Very sparse, sombre English music for a winter of starvation. A single bass viol plays long, slow, low notes "
              "with silence between them, and a lute plucks an occasional soft, dark chord. Almost still, cold and empty, "
              "grave and quiet, never dramatic."
              + ROOM, LOOP, "D minor", 52, "4", (61, 62)),
 "tobacco": ("A lively but uneasy English country dance for years of new money from a tobacco crop. A cittern and a lute "
             "strum a quick, busy rhythm, a recorder plays a bright tune with a restless, slightly anxious turn, a bass viol "
             "walks underneath, and a tabor keeps light time. Prosperous on the surface, uneasy underneath."
             + ROOM, LOOP, "G minor", 104, "4", (71, 72)),
}


def wf(name, seed):
    cap, sections, key, bpm, ts, _ = CUES[name]
    n = lambda ct, **i: {"class_type": ct, "inputs": i}
    return {
        "1": n("UNETLoader", unet_name="acestep_v1.5_xl_sft_bf16.safetensors", weight_dtype="default"),
        "2": n("DualCLIPLoader", clip_name1="qwen_0.6b_ace15.safetensors", clip_name2="qwen_1.7b_ace15.safetensors",
               type="ace", device="default"),
        "3": n("VAELoader", vae_name="ace_1.5_vae.safetensors"),
        "4": n("TextEncodeAceStepAudio1.5", clip=["2", 0], tags=cap, lyrics=sections, seed=seed, bpm=bpm,
               duration=float(SECS), timesignature=ts, language="en", keyscale=key, generate_audio_codes=True,
               cfg_scale=2.0, temperature=0.85, top_p=1.0, top_k=0, min_p=0.0),
        "5": n("ConditioningZeroOut", conditioning=["4", 0]),
        "6": n("EmptyAceStep1.5LatentAudio", seconds=float(SECS), batch_size=1),
        "7": n("ModelSamplingAuraFlow", model=["1", 0], shift=3.0),
        "8": n("KSampler", model=["7", 0], seed=seed, steps=50, cfg=7.0, sampler_name="euler", scheduler="simple",
               positive=["4", 0], negative=["5", 0], latent_image=["6", 0], denoise=1.0),
        "9": n("VAEDecodeAudio", samples=["8", 0], vae=["3", 0]),
        "10": n("SaveAudio", audio=["9", 0], filename_prefix="stickhistory_music/%s-s%d" % (name, seed)),
    }


def generate(jobs):
    sys.path.insert(0, r"E:\VN-Tools\asset-toolkit")
    from comfy import Comfy
    os.makedirs(RAW, exist_ok=True)
    with Comfy() as c:          # the whole batch inside one lease (LOCAL_AI.md Start here, rule 2)
        for name, seed in jobs:
            if glob.glob(os.path.join(RAW, "%s-s%d.*" % (name, seed))):
                continue
            files = c.run(wf(name, seed), RAW, timeout=2400)
            src = files[0] if isinstance(files, (list, tuple)) else files
            os.replace(src, os.path.join(RAW, "%s-s%d" % (name, seed) + os.path.splitext(src)[1]))
            print("music", name, seed, flush=True)


FOLD = 4.0        # seconds of the take's end folded over its start: the loop seam is a 4 s equal-power crossfade
TARGET_RMS = -20.0  # dBFS for the file; the game plays it far lower (MUSIC_VOL in index.html)
LEVEL = {"sickness": -22.0, "starving": -25.0}   # the sombre cues sit lower than the rest
OPUS = r"C:\Users\zachw\Texas Civilization\runtime\voice\bin\opusenc.exe"   # same encoder as tools/voice_build.py


def take_of(name):
    """the take that ships: the retry seed if one was made and chosen in KEEP, else the first seed"""
    seed = KEEP.get(name, CUES[name][5][0])
    hits = glob.glob(os.path.join(RAW, "%s-s%d.*" % (name, seed)))
    return (hits[0], seed) if hits else (None, seed)


KEEP = {}   # cue -> seed, when the retry replaced the first take


START = {"starving": 3.0}   # seconds skipped at the head; the starving take opens on a heavy low chord


def frames(m, sr, a, secs, hop=0.05, n=2048):
    """log spectra, 100 Hz - 4 kHz, every 50 ms over [a, a+secs): pitch AND rhythm, for matching two places"""
    import numpy as np
    h = int(hop * sr)
    idx = [int(a * sr) + i * h for i in range(int(secs / hop))]
    f = np.fft.rfftfreq(n, 1 / sr)
    band = (f > 100) & (f < 4000)
    out = np.array([np.log(np.abs(np.fft.rfft(m[i:i + n] * np.hanning(n)))[band] + 1e-6) for i in idx])
    out -= out.mean()
    return out.ravel() / (np.linalg.norm(out) + 1e-9)


def looped(x, sr, name):
    """Cut the loop [s, e) out of the take and fold x[e:e+FOLD] over its head, so the last sample runs
    straight on into the first. s skips the opening; e is searched for in the last stretch of real music
    (before the take's own ending and trailing silence) as the place that most resembles the head, so the
    crossfade joins like to like, in step with the beat."""
    import numpy as np
    m = x.mean(1)
    h = sr // 2
    env = np.array([20 * np.log10(np.sqrt((m[i:i + h] ** 2).mean()) + 1e-12) for i in range(0, len(m) - h + 1, h)])
    end = (np.where(env > np.median(env) - 25)[0][-1] + 1) / 2.0   # where the music stops
    s = START.get(name, 2.0)
    head = frames(m, sr, s, FOLD)
    best, e = -2, None
    for c in np.arange(max(s + 50, end - 16), end - 3 - FOLD, 0.05):
        sim = float(head @ frames(m, sr, c, FOLD))
        if sim > best:
            best, e = sim, c
    si, ei, f = int(s * sr), int(e * sr), int(FOLD * sr)
    t = np.linspace(0, np.pi / 2, f)[:, None]
    y = x[si:ei].copy()
    y[:f] = x[si:si + f] * np.sin(t) + x[ei:ei + f] * np.cos(t)
    return y, s, e, best


def measure(x, sr):
    import numpy as np
    m = x.mean(axis=1)
    rms = 20 * np.log10(np.sqrt((m ** 2).mean()) + 1e-12)
    peak = 20 * np.log10(np.abs(x).max() + 1e-12)
    # loudness every 2 s, to see sparse passages and any build or fade
    hop = 2 * sr
    env = [20 * np.log10(np.sqrt((m[i:i + hop] ** 2).mean()) + 1e-12) for i in range(0, len(m) - hop + 1, hop)]
    # spectral flatness (0 tonal .. 1 noise) and energy above 8 kHz: a synth pad is flat-steady and dark or buzzy
    spec = np.abs(np.fft.rfft(m[: (len(m) // 4096) * 4096].reshape(-1, 4096) * np.hanning(4096), axis=1)) + 1e-9
    flat = float(np.mean(np.exp(np.log(spec).mean(axis=1)) / spec.mean(axis=1)))
    freqs = np.fft.rfftfreq(4096, 1 / sr)
    hf = float(spec[:, freqs > 8000].sum() / spec.sum())
    return dict(secs=len(x) / sr, rms=rms, peak=peak, env=env, flat=flat, hf=hf)


def spectrogram(x, sr, png):
    """log-frequency spectrogram, 0-8 kHz, for looking at what was played"""
    import numpy as np
    from PIL import Image
    m = x.mean(axis=1)
    n, hop = 4096, 1024
    frames = np.lib.stride_tricks.sliding_window_view(m, n)[::hop] * np.hanning(n)
    s = 20 * np.log10(np.abs(np.fft.rfft(frames, axis=1)) + 1e-9)
    freqs = np.fft.rfftfreq(n, 1 / sr)
    rows = np.geomspace(60, 8000, 300)
    idx = np.searchsorted(freqs, rows)
    img = s[:, idx].T[::-1]
    img = np.clip((img - (img.max() - 80)) / 80, 0, 1)
    Image.fromarray((img * 255).astype("uint8")).resize((1200, 300)).save(png)


def encode(names, report_dir):
    import numpy as np, soundfile as sf, tempfile
    os.makedirs(OUT, exist_ok=True)
    for name in names:
        src, seed = take_of(name)
        if not src:
            print("music %-10s no take yet" % name); continue
        x, sr = sf.read(src, always_2d=True)
        raw = measure(x, sr)
        if report_dir:
            spectrogram(x, sr, os.path.join(report_dir, "%s-s%d.png" % (name, seed)))
        y, s0, e0, sim = looped(x, sr, name)
        g = 10 ** ((LEVEL.get(name, TARGET_RMS) - measure(y, sr)["rms"]) / 20)
        y = y * g
        pk = np.abs(y).max()
        if pk > 0.89:                     # keep 1 dB of headroom; a quiet cue is never pushed into clipping
            y *= 0.89 / pk
        wav = os.path.join(tempfile.gettempdir(), "sh_music_%s.wav" % name)
        sf.write(wav, y.astype("float32"), sr, subtype="FLOAT")
        dst = os.path.join(OUT, name + ".ogg")
        r = subprocess.run([OPUS, "--quiet", "--bitrate", "48", "--music", wav, dst], capture_output=True, text=True)
        os.remove(wav)
        out = measure(y, sr)
        print("music %-10s seed %d  take %.1fs rms %.1f peak %.1f flat %.3f hf %.3f | loop %.1f-%.1f (%.1fs, seam match %.2f) %s  %d KB  env %s"
              % (name, seed, raw["secs"], raw["rms"], raw["peak"], raw["flat"], raw["hf"], s0, e0, out["secs"], sim,
                 "ok" if r.returncode == 0 else "FAIL opus " + r.stderr[-200:],
                 os.path.getsize(dst) // 1024 if os.path.exists(dst) else 0,
                 " ".join("%.0f" % e for e in raw["env"])), flush=True)


if __name__ == "__main__":
    args = sys.argv[1:]
    names = [a for a in args if not a.startswith("--")] or list(CUES)
    if "--encode" in args:
        rep = next((a.split("=", 1)[1] for a in args if a.startswith("--report=")), None)
        encode(names, rep)
    else:
        retry = "--retry" in args
        generate([(n, CUES[n][5][1 if retry else 0]) for n in names])
