import subprocess
from pathlib import Path


def _esc_filter_path(p: str) -> str:
    return p.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def render_clip(video: str, segs: list[tuple[float, float]], ass_path: str, out: str,
                face_x: float, vcfg: dict) -> None:
    """Knip segmenten, plak ze aan elkaar, crop naar 9:16 rond het gezicht, brand captions in."""
    w, h, fps = vcfg["width"], vcfg["height"], vcfg["fps"]
    x_expr = f"max(0,min(iw-ow,{face_x:.4f}*iw-ow/2))"
    parts, labels = [], ""
    for i, (a, b) in enumerate(segs):
        parts.append(f"[0:v]trim={a:.3f}:{b:.3f},setpts=PTS-STARTPTS[v{i}]")
        parts.append(f"[0:a]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS[a{i}]")
        labels += f"[v{i}][a{i}]"
    parts.append(f"{labels}concat=n={len(segs)}:v=1:a=1[cv][ca]")
    parts.append(f"[cv]crop=w='min(iw,ih*{w}/{h})':h=ih:x='{x_expr}':y=0,"
                 f"scale={w}:{h}:flags=lanczos,setsar=1,fps={fps},"
                 f"ass='{_esc_filter_path(ass_path)}'[vout]")
    parts.append("[ca]loudnorm=I=-14:TP=-1.5:LRA=11[aout]")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-filter_complex", ";".join(parts),
           "-map", "[vout]", "-map", "[aout]", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-ar", "44100",
           "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)


def download(url: str, dest_dir: str) -> str:
    """Download een URL met yt-dlp en geef het bestandspad terug."""
    out = str(Path(dest_dir) / "source.%(ext)s")
    subprocess.run(["yt-dlp", "-f", "bv*[height<=1080]+ba/b", "--merge-output-format", "mp4",
                    "-o", out, url], check=True)
    return str(next(Path(dest_dir).glob("source.*")))
