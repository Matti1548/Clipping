#!/usr/bin/env python3
"""Demo zonder Whisper/API: testvideo met bewegende 'spreker' + nagemaakt Engels transcript."""
import subprocess
import sys
from pathlib import Path

from autoclip.config import load_config
from autoclip.models import Highlight, Word
from autoclip.pipeline import make_clip
from autoclip.profiles import apply_profile

out = Path(sys.argv[1] if len(sys.argv) > 1 else "demo_output")
out.mkdir(exist_ok=True)
src = out / "bron.mp4"
# rode blokje = "spreker" die van links naar rechts loopt; geluid met pieken
subprocess.run(["ffmpeg", "-y", "-loglevel", "error",
                "-f", "lavfi", "-i", "color=c=0x223344:s=1280x720:d=30:r=25",
                "-f", "lavfi", "-i", "color=c=red:s=160x160:d=30:r=25",
                "-f", "lavfi", "-i", "sine=f=300:d=30",
                "-filter_complex", "[0][1]overlay=x='(W-w)*t/30':y=280",
                "-shortest", str(src)], check=True)

text = ("So um this is the biggest mistake creators make. Uh nobody tells you this. "
        "First you cut every silence. Then um you add captions. That is why people keep watching.")
words, t = [], 2.0
for w in text.split():
    words.append(Word(w, t, t + 0.4))
    t += 0.45
    if w.endswith("."):
        t += 1.5
h = Highlight(2.0, words[-1].end + 0.2, 9, "demo", hook="The biggest mistake creators make")

for ctype in ("podcast", "gaming"):
    cfg = apply_profile(load_config("config.yaml"), ctype)
    # nagebootst 'gezichtstracking': het blokje loopt van links naar rechts
    keys = [(s, (80 + 1120 * s / 30) / 1280) for s in [x / 2 for x in range(4, 50)]]
    import autoclip.pipeline as pl
    pl.face_track = lambda *a, k=keys: k   # echte detectie vereist een echt gezicht
    make_clip(str(src), words, h, out, ctype, cfg)
    print(ctype, "->", out / f"{ctype}.mp4")
