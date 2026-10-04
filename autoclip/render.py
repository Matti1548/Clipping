import subprocess
from pathlib import Path


def _esc_filter_path(p: str) -> str:
    return p.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def render_clip(video: str, start: float, end: float, ass_path: str, out: str,
                face_x: float, vcfg: dict) -> None:
    """Knip, crop naar 9:16 rond het gezicht, schaal en brand de captions in."""
    w, h, fps = vcfg["width"], vcfg["height"], vcfg["fps"]
    x_expr = f"max(0,min(iw-ow,{face_x:.4f}*iw-ow/2))"
    vf = (f"crop=w='min(iw,ih*{w}/{h})':h=ih:x='{x_expr}':y=0,"
          f"scale={w}:{h}:flags=lanczos,setsar=1,fps={fps},"
          f"ass='{_esc_filter_path(ass_path)}'")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start:.3f}", "-to", f"{end:.3f}",
           "-i", video, "-vf", vf, "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)


def download(url: str, dest_dir: str) -> str:
    """Download een URL met yt-dlp en geef het bestandspad terug."""
    out = str(Path(dest_dir) / "source.%(ext)s")
    subprocess.run(["yt-dlp", "-f", "bv*[height<=1080]+ba/b", "--merge-output-format", "mp4",
                    "-o", out, url], check=True)
    return str(next(Path(dest_dir).glob("source.*")))
