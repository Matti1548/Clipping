#!/usr/bin/env python3
"""Demo zonder Whisper/API: testvideo + nagemaakt transcript + voorbeeld-campagnebrief."""
import json
import subprocess
import sys
from pathlib import Path

import autoclip.pipeline as pl
from autoclip.config import load_config
from autoclip.models import Highlight, Word
from autoclip.profiles import apply_profile
from autoclip.rules import apply_to_config, parse_rules_regex, read_document

out = Path(sys.argv[1] if len(sys.argv) > 1 else "demo_output")
out.mkdir(exist_ok=True)
src, music_dir, bg_dir = out / "bron.mp4", out / "music", out / "backgrounds"
music_dir.mkdir(exist_ok=True)
bg_dir.mkdir(exist_ok=True)
ff = ["ffmpeg", "-y", "-loglevel", "error"]
subprocess.run(ff + ["-f", "lavfi", "-i", "color=c=0x223344:s=1280x720:d=40:r=25",
                     "-f", "lavfi", "-i", "color=c=red:s=160x160:d=40:r=25", "-f", "lavfi", "-i", "sine=f=300:d=40",
                     "-filter_complex", "[0][1]overlay=x='(W-w)*t/40':y=280", "-shortest", str(src)], check=True)
# zelfgemaakte (rechtenvrije) assets: een akkoord als 'muziek' en een gradient als achtergrondbeeld
subprocess.run(ff + ["-f", "lavfi", "-i", "sine=f=220:d=20", "-f", "lavfi", "-i", "sine=f=277:d=20",
                     "-filter_complex", "amix=inputs=2", str(music_dir / "chill_loop.mp3")], check=True)
subprocess.run(ff + ["-f", "lavfi", "-i", "gradients=s=1080x1920:d=10:r=25:c0=0x6a11cb:c1=0x2575fc:speed=0.05",
                     "-pix_fmt", "yuv420p", str(bg_dir / "purple_flow.mp4")], check=True)

text = ("So um this is the biggest mistake creators make with their gym routine. Nobody tells you this. "
        "Uh first you track every single workout so you can see real progress. Then um you plan your week. "
        "That is why I use NovaFit every day. Also FitBrand never worked for me. It keeps me honest and consistent. "
        "Give it a try and see the difference for yourself.")
words, t = [], 2.0
for w in text.split():
    words.append(Word(w, t, t + 0.4))
    t += 0.45
    if w.endswith("."):
        t += 1.2
h = Highlight(2.0, words[-1].end + 0.2, 9, "demo", hook="The biggest gym mistake")

brief = read_document("examples/campaign_novafit.md")
rules = parse_rules_regex(brief)
(out / "rules_parsed.json").write_text(json.dumps(rules, indent=2))
print("Regels uit brief:", {k: v for k, v in rules.items() if v not in (None, [], "") and k != "notes"})


def scenario(name, ctype, rule_overrides=None, force_bg=False):
    r = {**rules, **(rule_overrides or {})}
    cfg = apply_to_config(apply_profile(load_config("config.yaml"), ctype), r)
    cfg["video"]["face_tracking"] = False
    cfg["background"].update(music_dir=str(music_dir), video_dir=str(bg_dir))
    if force_bg:  # zonder LLM kiest de fallback nooit een achtergrondbeeld; hier forceren we het
        orig = pl.decide
        pl.decide = lambda *a, **k: {"music": None, "background": str(bg_dir / "purple_flow.mp4"), "reason": "demo"}
    pl.make_clip(str(src), words, h, out, name, cfg)
    if force_bg:
        pl.decide = orig
    d = json.loads((out / f"{name}.json").read_text())
    print(f"\n[{name}] {d['duration']}s | achtergrond: {d['background']}")
    print("  titel:", d["title"], "\n  caption:", d["caption"], "\n  hashtags:", " ".join(d["hashtags"]))
    for c in d["compliance"]["checks"]:
        print(f"  {'✓' if c['ok'] else ('?' if c['ok'] is None else '✗')} {c['check']} {c['detail']}")
    print("  => compliant:", d["compliance"]["compliant"])


scenario("vlog_met_muziek", "vlog")
scenario("vlog_muziek_verboden", "vlog", {"allow_music": False})
scenario("gaming_achtergrondbeeld", "gaming", force_bg=True)
