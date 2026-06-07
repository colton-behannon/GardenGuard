from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
import yaml

from gardenguard.camera.capture import Camera
from gardenguard.detection.motion import MotionDetector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "settings.yaml"


def _load_config() -> dict:
    with _CONFIG_PATH.open() as f:
        return yaml.safe_load(f)


def _annotate(frame: np.ndarray, detections: list[dict], roi_points: list[list[int]]) -> np.ndarray:
    annotated = frame.copy()
    pts = np.array(roi_points, dtype=np.int32)
    cv2.polylines(annotated, [pts], isClosed=True, color=(0, 255, 255), thickness=2)
    for det in detections:
        x, y, w, h = det["x"], det["y"], det["w"], det["h"]
        cv2.rectangle(annotated, (x, y), (x + w, y + h), color=(0, 0, 255), thickness=2)
        cv2.putText(
            annotated,
            f"motion {det['area']}px",
            (x, max(y - 8, 0)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 0, 255),
            1,
            cv2.LINE_AA,
        )
    return annotated


def main() -> None:
    config = _load_config()
    cam_cfg = config["camera"]
    mot_cfg = config["motion"]

    captures_dir = Path(config["paths"]["captures_dir"])
    logs_dir = Path(config["paths"]["logs_dir"])
    captures_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    log_path = logs_dir / "detections.jsonl"

    detector = MotionDetector(
        min_area=mot_cfg["min_area"],
        learning_rate=mot_cfg["learning_rate"],
        roi_points=mot_cfg["roi"],
        warmup_frames=mot_cfg.get("warmup_frames", 30),
    )

    log.info("GardenGuard Phase 2 - motion detection loop starting")

    with Camera(width=cam_cfg["width"], height=cam_cfg["height"]) as cam:
        try:
            while True:
                frame = cam.capture_frame()
                detections = detector.detect(frame)

                if detections:
                    ts = datetime.now(timezone.utc)
                    ts_str = ts.strftime("%Y%m%dT%H%M%S%f")[:-3] + "Z"
                    filename = f"motion_{ts_str}.jpg"
                    save_path = captures_dir / filename

                    annotated = _annotate(frame, detections, mot_cfg["roi"])
                    cv2.imwrite(str(save_path), annotated)

                    event = {
                        "timestamp": ts.isoformat(),
                        "frame": str(save_path),
                        "detections": detections,
                    }
                    with log_path.open("a") as f:
                        f.write(json.dumps(event) + "\n")

                    log.info(
                        "Motion detected: %d region(s) -> %s", len(detections), save_path
                    )

        except KeyboardInterrupt:
            log.info("Shutting down � KeyboardInterrupt")


if __name__ == "__main__":
    main()