#!/usr/bin/env python3
"""Demo zonder Whisper/API: testvideo + nagemaakt transcript met pauzes."""
import json
import subprocess
import sys
from pathlib import Path

from autoclip.config import load_config
from autoclip.models import Highlight, Word
from autoclip.pipeline import make_clip

out = Path(sys.argv[1] if len(sys.argv) > 1 else "demo_output")
out.mkdir(exist_ok=True)
src = out / "bron.mp4"
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc2=s=1280x720:d=30:r=25",
                "-f", "lavfi", "-i", "sine=f=300:d=30", "-shortest", str(src)], check=True)

text = ("Dit is het geheim van goede clips. Niemand vertelt je dit. "
        "Eerst knip je alle stiltes weg. Daarna voeg je captions toe. Zo blijft iedereen kijken.")
words, t = [], 2.0
for w in text.split():
    words.append(Word(w, t, t + 0.4))
    t += 0.45
    if w.endswith("."):
        t += 2.0  # lange pauze na elke zin

cfg = load_config("config.yaml")
cfg["video"]["face_tracking"] = False
h = Highlight(2.0, words[-1].end + 0.2, 9, "demo", hook="Het geheim van goede clips")

for tighten in (False, True):
    cfg["video"]["tighten_pauses"] = tighten
    name = "met_pauzes" if not tighten else "ingekort"
    make_clip(str(src), words, h, out, name, cfg)
    d = json.loads((out / f"{name}.json").read_text())
    print(f"{name:12s} duur: {d['duration']:.1f}s")
