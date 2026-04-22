from __future__ import annotations

import numpy as np
from picamera2 import Picamera2


class Camera:
    """Context manager that wraps Picamera2 and yields BGR numpy frames.

    Uses a video configuration for low-latency continuous capture, which
    is suitable for real-time monitoring. Frames are returned as (H, W, 3)
    uint8 arrays in BGR channel order (OpenCV-compatible).

    Usage:
        with Camera(width=1536, height=864) as cam:
            frame = cam.capture_frame()
    """

    def __init__(self, width: int, height: int) -> None:
        self._width = width
        self._height = height
        self._cam: Picamera2 | None = None

    def __enter__(self) -> Camera:
        self._cam = Picamera2()
        config = self._cam.create_video_configuration(
            main={"size": (self._width, self._height), "format": "BGR888"}
        )
        self._cam.configure(config)
        self._cam.start()
        return self

    def __exit__(self, *args: object) -> None:
        if self._cam is not None:
            self._cam.stop()
            self._cam.close()
            self._cam = None

    def capture_frame(self) -> np.ndarray:
        """Return the latest frame as a (H, W, 3) BGR uint8 numpy array."""
        if self._cam is None:
            raise RuntimeError("Camera is not open. Use Camera as a context manager.")
        return self._cam.capture_array("main")
