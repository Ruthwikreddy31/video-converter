"""
Smart crop subject detection.

DESIGN NOTE: Earlier versions tried ThreadPoolExecutor and then a subprocess
to isolate OpenCV calls with a timeout. Both approaches turned out to be
unreliable across different Windows setups (venv wrappers, IDE run configs,
DLL path issues, COM threading quirks) — the call could still hang or fail
to even launch, with no clean way to detect that from the caller's side.

This version takes a different approach: a SINGLE, FAST in-process OpenCV
call with NO threading/subprocess wrapper at all (removing an entire class
of platform-specific hang). To keep the same goal — never block conversion
for long — the detection work itself is reduced to the bare minimum (open
video, grab exactly one frame, run only fast Haar-cascade detection) and
any exception at any point is caught immediately and falls back to center
crop. If this still does not return within the caller's expectations, the
crop_method should simply be set to "center" from the frontend to skip
detection entirely (see convert.py — center crop never touches OpenCV).
"""
import os
from typing import Optional, Dict, Any


def get_smart_crop_or_center(video_path: str, width: int, height: int) -> Dict[str, Any]:
    """
    Get smart crop coordinates. Always returns a valid dict immediately —
    never raises. Falls back to plain center crop on any failure.
    """
    fallback = {
        "center_x": width // 2,
        "center_y": height // 2,
        "method": "center",
        "confidence": 1.0,
    }

    abs_path = os.path.abspath(video_path)
    if not os.path.isfile(abs_path):
        print(f"[smart_crop] File not found: {abs_path} — using center crop")
        return fallback

    cap = None
    try:
        import cv2

        cap = cv2.VideoCapture(abs_path)
        if not cap.isOpened():
            print(f"[smart_crop] cv2.VideoCapture could not open file — using center crop")
            return fallback

        # Grab a single frame near the start — avoid seeking, which is the
        # part most likely to stall on certain codecs/backends. Reading
        # sequentially from frame 0 is the most universally reliable
        # operation across OpenCV backends.
        ret, frame = cap.read()

        if not ret or frame is None:
            print("[smart_crop] Could not read a frame — using center crop")
            return fallback

        h, w = frame.shape[:2]

        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        if not os.path.exists(cascade_path):
            print("[smart_crop] Haar cascade file missing — using center crop")
            return fallback

        face_cascade = cv2.CascadeClassifier(cascade_path)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        scale = min(1.0, 640 / max(w, h))
        if scale < 1.0:
            gray = cv2.resize(gray, (int(w * scale), int(h * scale)))

        faces = face_cascade.detectMultiScale(
            gray, scaleFactor=1.2, minNeighbors=4, minSize=(24, 24)
        )

        if len(faces) == 0:
            print("[smart_crop] No faces found — using center crop")
            return fallback

        if scale < 1.0:
            faces = [(int(x/scale), int(y/scale), int(fw/scale), int(fh/scale)) for x, y, fw, fh in faces]

        all_cx = [x + fw // 2 for x, y, fw, fh in faces]
        all_cy = [y + fh // 2 for x, y, fw, fh in faces]

        result = {
            "center_x": int(sum(all_cx) / len(all_cx)),
            "center_y": int(sum(all_cy) / len(all_cy)),
            "method": "face_detection",
            "confidence": 0.9,
            "subjects_found": len(faces),
        }
        print(f"[smart_crop] Detected: {result}")
        return result

    except ImportError:
        print("[smart_crop] OpenCV (cv2) not installed — using center crop")
        return fallback
    except Exception as e:
        print(f"[smart_crop] Detection error: {e} — using center crop")
        return fallback
    finally:
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass
