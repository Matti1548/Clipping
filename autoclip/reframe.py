"""Gezichtstracking: bepaal de horizontale crop-positie voor 9:16."""
import statistics


def face_center_x(video: str, start: float, end: float, step: float = 0.5) -> float:
    """Mediaan van het x-midden (0..1) van het grootste gezicht; 0.5 als er geen gezicht is."""
    try:
        import cv2
    except ImportError:
        return 0.5
    cap = cv2.VideoCapture(video)
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    xs, t = [], start
    while t < end:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = cap.read()
        if not ok:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(gray, 1.2, 5, minSize=(60, 60))
        if len(faces):
            x, _, w, _ = max(faces, key=lambda f: f[2] * f[3])
            xs.append((x + w / 2) / frame.shape[1])
        t += step
    cap.release()
    return statistics.median(xs) if xs else 0.5
