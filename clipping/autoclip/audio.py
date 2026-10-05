"""Audio-energie per seconde (0..1): hard geluid = schreeuwen, lachen, actie."""
import subprocess

import numpy as np


def energy_per_second(video: str, rate: int = 8000) -> np.ndarray:
    proc = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", video, "-vn", "-ac", "1", "-ar", str(rate),
                           "-f", "s16le", "-"], capture_output=True)
    pcm = np.frombuffer(proc.stdout, dtype=np.int16).astype(np.float32)
    n = len(pcm) // rate
    if n == 0:
        return np.zeros(0)
    rms = np.sqrt((pcm[: n * rate].reshape(n, rate) ** 2).mean(axis=1))
    peak = rms.max()
    return rms / peak if peak > 0 else rms


def mean_energy(energy: np.ndarray, start: float, end: float) -> float:
    seg = energy[int(start): int(end) + 1]
    return float(seg.mean()) if len(seg) else 0.0
