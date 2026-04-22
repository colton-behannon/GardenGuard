from __future__ import annotations

import logging
from pathlib import Path

import cv2
import yaml

from gardenguard.camera.capture import Camera

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


def main() -> None:
    config = _load_config()
    cam_cfg = config["camera"]
    captures_dir = Path(config["paths"]["captures_dir"])
    captures_dir.mkdir(parents=True, exist_ok=True)

    log.info("GardenGuard Phase 1 — camera test")

    with Camera(width=cam_cfg["width"], height=cam_cfg["height"]) as cam:
        frame = cam.capture_frame()
        log.info("Captured frame  shape=%s  dtype=%s", frame.shape, frame.dtype)

        out_path = captures_dir / "test_capture.jpg"
        cv2.imwrite(str(out_path), frame)
        log.info("Saved test frame → %s", out_path)


if __name__ == "__main__":
    main()
