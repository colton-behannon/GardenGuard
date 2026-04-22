"""Phase 1 camera smoke tests.

These tests must run on the Raspberry Pi with the Camera Module 3 connected.
They will not pass on a laptop (no picamera2/libcamera available outside the Pi).

Run with:
    pytest tests/test_capture.py -v
"""
import numpy as np
import pytest

from gardenguard.camera.capture import Camera

WIDTH = 1536
HEIGHT = 864


def test_capture_frame_shape():
    """Camera returns an array with the configured (H, W, 3) shape."""
    with Camera(width=WIDTH, height=HEIGHT) as cam:
        frame = cam.capture_frame()

    assert isinstance(frame, np.ndarray), "Frame must be a numpy array"
    assert frame.shape == (HEIGHT, WIDTH, 3), f"Unexpected shape: {frame.shape}"


def test_capture_frame_dtype():
    """Camera frames are uint8 (0–255 per channel)."""
    with Camera(width=WIDTH, height=HEIGHT) as cam:
        frame = cam.capture_frame()

    assert frame.dtype == np.uint8, f"Expected uint8, got {frame.dtype}"


def test_capture_multiple_frames():
    """Camera returns consistent shapes across multiple consecutive captures."""
    with Camera(width=WIDTH, height=HEIGHT) as cam:
        frames = [cam.capture_frame() for _ in range(5)]

    assert len(frames) == 5
    for i, frame in enumerate(frames):
        assert frame.shape == (HEIGHT, WIDTH, 3), f"Frame {i} has unexpected shape: {frame.shape}"


def test_camera_closed_raises():
    """Calling capture_frame outside a context manager raises RuntimeError."""
    cam = Camera(width=WIDTH, height=HEIGHT)
    with pytest.raises(RuntimeError, match="context manager"):
        cam.capture_frame()
