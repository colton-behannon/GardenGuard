#!/usr/bin/env bash
# Run this script directly on the Raspberry Pi Zero 2 W (not from your laptop).
# It installs system dependencies, enables the camera and pigpiod, and creates
# a Python venv that can access the apt-installed picamera2/libcamera bindings.
#
# Usage:
#   bash scripts/pi_setup.sh
set -euo pipefail

VENV_DIR="${HOME}/gardenguard-env"
BOOT_CONFIG="/boot/firmware/config.txt"

echo "=== GardenGuard Pi Setup ==="
echo ""

# --- 1. System packages ---
echo "[1/5] Installing system packages..."
sudo apt update -qq
sudo apt install -y \
    python3-picamera2 \
    python3-opencv \
    python3-pigpio \
    python3-yaml \
    pigpio
echo "      Done."

# --- 2. Enable camera ---
echo "[2/5] Enabling camera..."
if ! grep -q "^camera_auto_detect=1" "${BOOT_CONFIG}"; then
    echo "camera_auto_detect=1" | sudo tee -a "${BOOT_CONFIG}" > /dev/null
    echo "      Added camera_auto_detect=1 to ${BOOT_CONFIG}"
else
    echo "      camera_auto_detect already set — skipping."
fi

# --- 3. Enable pigpiod service ---
echo "[3/5] Enabling pigpiod service..."
sudo systemctl enable --now pigpiod
echo "      pigpiod enabled and started."

# --- 4. Create Python venv ---
echo "[4/5] Creating Python venv at ${VENV_DIR}..."
# --system-site-packages is required so the venv can access the apt-installed
# picamera2 and libcamera Python bindings (they are not available on PyPI).
python3 -m venv "${VENV_DIR}" --system-site-packages
echo "      Venv created with --system-site-packages."

# --- 5. Install dev tools into venv ---
echo "[5/5] Installing dev tools into venv..."
# shellcheck source=/dev/null
source "${VENV_DIR}/bin/activate"
pip install --quiet "pytest>=8.0" "ruff>=0.4" "pyyaml>=6.0"
deactivate
echo "      Done."

echo ""
echo "=== Setup complete ==="
echo ""
echo "IMPORTANT: reboot to activate the camera before first use:"
echo "  sudo reboot"
echo ""
echo "After reboot, deploy from your laptop:"
echo "  PI_HOST=pi@<ip_address> bash scripts/deploy.sh"
echo ""
echo "Then SSH to the Pi and run:"
echo "  source ${VENV_DIR}/bin/activate"
echo "  cd ~/gardenguard"
echo "  python -m gardenguard.main"
