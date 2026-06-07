from __future__ import annotations

import cv2
import numpy as np


class MotionDetector:
    """OpenCV MOG2-based motion detector with ROI polygon masking.

    Applies a background subtractor to each frame, restricts detections to a
    configurable pixel polygon (the garden bed), and returns bounding boxes for
    any moving regions larger than ``min_area`` pixels�.
    """

    def __init__(
        self,
        min_area: int,
        learning_rate: float,
        roi_points: list[list[int]],
        warmup_frames: int = 30,
    ) -> None:
        self._subtractor = cv2.createBackgroundSubtractorMOG2(detectShadows=True)
        self._min_area = min_area
        self._learning_rate = learning_rate
        self._roi_points = np.array(roi_points, dtype=np.int32)
        self._roi_mask: np.ndarray | None = None
        self._kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        self._warmup_frames = warmup_frames
        self._frame_count = 0

    def _build_roi_mask(self, shape: tuple[int, ...]) -> None:
        mask = np.zeros(shape[:2], dtype=np.uint8)
        cv2.fillPoly(mask, [self._roi_points], 255)
        self._roi_mask = mask

    def detect(self, frame: np.ndarray) -> list[dict[str, int]]:
        """Return bounding boxes for motion events within the ROI.

        Args:
            frame: BGR uint8 array of shape (H, W, 3).

        Returns:
            List of dicts with keys ``x``, ``y``, ``w``, ``h``, ``area``.
            Empty list when no motion exceeds ``min_area``.
        """
        if self._roi_mask is None:
            self._build_roi_mask(frame.shape)

        self._frame_count += 1
        # Always feed frames to MOG2 so it learns the background during warmup,
        # but suppress detections until the model has stabilised.
        fg_mask = self._subtractor.apply(frame, learningRate=self._learning_rate)
        if self._frame_count <= self._warmup_frames:
            return []

        # MOG2 marks shadows as 127; threshold to keep only foreground (255).
        fg_mask = cv2.threshold(fg_mask, 200, 255, cv2.THRESH_BINARY)[1]

        fg_mask = cv2.bitwise_and(fg_mask, self._roi_mask)

        # Morphological cleanup: remove noise, fill small gaps.
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, self._kernel)
        fg_mask = cv2.dilate(fg_mask, self._kernel, iterations=2)

        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        detections: list[dict[str, int]] = []
        for cnt in contours:
            area = int(cv2.contourArea(cnt))
            if area >= self._min_area:
                x, y, w, h = cv2.boundingRect(cnt)
                detections.append({"x": int(x), "y": int(y), "w": int(w), "h": int(h), "area": area})

        return detections