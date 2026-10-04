"""Dynamische gezichtstracking: een vloeiend pad van crop-posities (x, 0..1) door de tijd."""
import statistics


def detect_faces(video: str, start: float, end: float, step: float = 0.4) -> list[tuple[float, float | None]]:
    """(tijd, x-midden van het grootste gezicht of None) per sample."""
    try:
        import cv2
    except ImportError:
        return []
    cap = cv2.VideoCapture(video)
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    out, t = [], start
    while t < end:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = cap.read()
        if not ok:
            break
        faces = cascade.detectMultiScale(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), 1.2, 5, minSize=(60, 60))
        if len(faces):
            x, _, w, _ = max(faces, key=lambda f: f[2] * f[3])
            out.append((t, (x + w / 2) / frame.shape[1]))
        else:
            out.append((t, None))
        t += step
    cap.release()
    return out


def smooth_track(samples: list[tuple[float, float | None]], window: int = 5,
                 deadzone: float = 0.05, every: int = 2) -> list[tuple[float, float]]:
    """Gaten vullen, mediaanfilter tegen uitschieters, deadzone tegen getril, daarna uitdunnen."""
    known = [x for _, x in samples if x is not None]
    if not known:
        return []
    xs, last = [], statistics.median(known)
    for _, x in samples:
        last = x if x is not None else last
        xs.append(last)
    h = window // 2
    med = [statistics.median(xs[max(0, i - h): i + h + 1]) for i in range(len(xs))]
    held, cur = [], med[0]
    for x in med:
        if abs(x - cur) > deadzone:
            cur = x
        held.append(cur)
    keys = [(samples[i][0], held[i]) for i in range(0, len(samples), every)]
    if keys[-1][0] != samples[-1][0]:
        keys.append((samples[-1][0], held[-1]))
    return keys


def face_track(video: str, start: float, end: float) -> list[tuple[float, float]]:
    return smooth_track(detect_faces(video, start, end))
