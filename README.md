# GardenGuard — Squirrel Defense Turret

An automated squirrel detection and water deterrent system built on Raspberry Pi Zero 2 W.
Detects squirrels in a raised garden bed via camera, aims a pan/tilt water turret, and fires.

---

## Hardware

### Phase 1 (owned)
| Item | Notes |
|---|---|
| Raspberry Pi Zero 2 W | Quad-core Cortex-A53 @ 1GHz, 512MB RAM |
| Raspberry Pi Camera Module 3 | IMX708, 12MP, 66° diagonal FoV (~54°H × 41°V) |
| Standard→Mini CSI adapter | Required for Camera Module 3 on Zero 2 W |

### Phases 4–5 (to purchase)
| Item | Notes |
|---|---|
| 2× MG90S servo | Metal gears; handles hose weight better than SG90 |
| Pan/tilt bracket kit | ~$5–8, widely available |
| Small submersible or peristaltic pump | |
| 5V relay module or IRLZ44N MOSFET | For pump switching |
| 5V 3A power supply (separate) | Servos + pump must NOT share Pi's 5V pin |
| Heatsink sticker for Pi Zero 2 W | Prevents throttling under sustained ML load |
| Waterproof enclosure | Pi lives outdoors |

---

## Project Structure

```
GardenGuard/
├── project.md
├── pyproject.toml
├── .gitignore
├── config/
│   └── settings.yaml           # resolution, paths, thresholds, GPIO pins
├── src/
│   └── gardenguard/
│       ├── __init__.py
│       ├── camera/
│       │   ├── __init__.py
│       │   └── capture.py      # picamera2 context-manager → BGR numpy arrays
│       ├── detection/
│       │   ├── __init__.py
│       │   ├── motion.py       # Phase 2: OpenCV MOG2 background subtractor
│       │   └── model.py        # Phase 3: NCNN YOLOv8-nano squirrel classifier
│       ├── turret/
│       │   ├── __init__.py
│       │   ├── servos.py       # Phase 4: pan/tilt via gpiozero + pigpio
│       │   └── pump.py         # Phase 4: relay-controlled water pump
│       └── main.py
├── models/                     # NCNN model files (git-ignored)
├── captures/                   # Saved detection frames (git-ignored)
├── logs/                       # JSONL event log (git-ignored)
├── scripts/
│   ├── pi_setup.sh             # One-shot Pi provisioning (run on Pi)
│   └── deploy.sh               # rsync from laptop → Pi over SSH
└── tests/
    ├── __init__.py
    └── test_capture.py         # Phase 1: camera smoke test (run on Pi)
```

---

## Development Workflow

Code is written on a desktop, deployed to the Pi via `rsync` over SSH.

```bash
# First time: provision the Pi
ssh pi@<ip_address> 'bash -s' < scripts/pi_setup.sh

# Every deploy
PI_HOST=pi@<ip_address> bash scripts/deploy.sh

# Run on Pi
ssh pi@<ip_address>
cd ~/gardenguard && source ~/gardenguard-env/bin/activate
python -m gardenguard.main
```

---

## Phases

### Phase 1 — Foundation ✅
**Goal**: working project skeleton; camera takes a frame; deploy pipeline verified.

- [x] `pyproject.toml` with `pytest` and `ruff` as dev tools
- [x] `config/settings.yaml` — camera resolution, output paths
- [x] `src/gardenguard/camera/capture.py` — `Camera` context manager wrapping `picamera2`
- [x] `src/gardenguard/main.py` — opens camera, captures one frame, logs shape, saves JPEG
- [x] `scripts/pi_setup.sh` — installs system deps, enables camera, enables `pigpiod`, creates venv
- [x] `scripts/deploy.sh` — rsync deploy to Pi
- [x] `tests/test_capture.py` — frame shape/dtype assertions

**Verification**:
```bash
# On Pi, inside venv
pytest tests/test_capture.py -v
python -m gardenguard.main
# Expect: "Captured frame shape: (864, 1536, 3)" and a file in captures/
```

---

### Phase 2 — Motion Detection
**Goal**: when anything moves in the garden bed ROI, save an annotated snapshot and log a JSON event.

**New files**:
- `src/gardenguard/detection/motion.py` — OpenCV `MOG2` background subtractor; configurable `min_area`; ROI polygon mask defined in `settings.yaml`

**Config additions** (`settings.yaml`):
```yaml
motion:
  min_area: 1500        # px² — tune to filter wind/leaves
  learning_rate: 0.005  # lower = slower background adaptation
  roi:                  # pixel polygon bounding your garden bed
    - [100, 200]
    - [1400, 200]
    - [1400, 700]
    - [100, 700]
```

**Updated `main.py`**: capture loop → run MOG2 → on trigger, draw bounding boxes, save annotated frame, append JSON line to `logs/detections.jsonl`.

---

### Phase 3 — Squirrel Classification + Notifications
**Goal**: confirm detections are actually squirrels with a custom ML model; send a phone notification with a snapshot.

**ML approach**:
- Dataset: Roboflow Universe (public squirrel datasets) — ~200–400 labeled images
- Model: YOLOv8-nano trained on Roboflow, exported to **NCNN format**
  - NCNN is ~3.7× faster than TFLite on ARM Cortex-A53
  - Target: ~3–5 FPS at 320×320 input on Pi Zero 2 W
- Why not a COCO model? COCO's 80 classes don't include squirrels

**New files**:
- `src/gardenguard/detection/model.py` — loads NCNN model, runs inference on motion-triggered crops, returns bounding boxes + confidence scores

**Notifications** (choose one at implementation time):
- **ntfy.sh** — zero-config push to phone; `pip install requests` only
- **Telegram bot** — `pip install python-telegram-bot`; requires creating a bot via @BotFather

**Updated `main.py`**: motion triggers → ML confirms squirrel → log event with bounding box → send notification with JPEG attachment.

---

### Phase 4 — Physical Turret
**Goal**: wire up servos + pump; verify with manual test script before integration.

**New files**:
- `src/gardenguard/turret/servos.py` — `gpiozero` `Servo` on GPIO 12 (pan) + GPIO 13 (tilt) using `PiGPIOFactory` (hardware PWM, no jitter); configurable angle limits
- `src/gardenguard/turret/pump.py` — `gpiozero` `OutputDevice` on relay GPIO pin; `pulse(duration_s)` method
- `scripts/test_turret.py` — interactive manual test: sweep servos, fire pump

**Servo wiring notes**:
- Signal wire → GPIO 12 (pan) or GPIO 13 (tilt)
- Power (red) → external 5V rail (NOT Pi 5V pin)
- Ground → shared ground with Pi
- Hardware PWM available on GPIO: 12, 13, 18, 19
- PWM: 50Hz, 1.0ms=0°, 1.5ms=90°, 2.0ms=180° (stay within this range until servo verified)

---

### Phase 5 — Auto-Aim & Full Pipeline
**Goal**: detected squirrel → turret aims → fires → cooldown → repeat.

**Camera FoV math**:
- Camera Module 3 at 1536×864: ~54° H × 41° V
- Degrees-per-pixel: `54/1536 ≈ 0.035°/px` (H), `41/864 ≈ 0.047°/px` (V)
- Bounding box center `(cx, cy)` → servo angle offset from center:
  - `pan_delta = (cx - width/2) * (H_fov / width)`
  - `tilt_delta = (cy - height/2) * (V_fov / height)`

**Updated `main.py`**: full pipeline with configurable cooldown (seconds between firings per target) and per-target re-fire suppression.

---

## Technical Notes

### picamera2 & virtual environments
`picamera2` and its `libcamera` C++ bindings are only available via `apt`, not `pip`.
The project venv is created with `--system-site-packages` so it can access these apt-installed packages.
Do **not** run `pip install picamera2` — the pip version lacks the compiled bindings.

### GPIO and servo PWM
Default `gpiozero` uses software PWM which causes visible jitter on servos.
The `pigpio` daemon provides hardware PWM. The setup script enables `pigpiod` as a systemd service.
Set the pin factory via environment variable or in code:
```bash
export GPIOZERO_PIN_FACTORY=pigpio
```

### Inference format choice
NCNN is chosen over TFLite for ARM because it's 3–5× faster on Cortex-A53.
At 320×320 int8, target inference speed is 3–5 FPS — sufficient for a slow-moving garden target.
Model is stored in `models/` (git-ignored due to size); documented download/conversion steps will be added in Phase 3.

### Power
Servos and pump draw significant current. Power them from a dedicated 5V 3A supply.
Never power servo red wire directly from the Pi's 5V GPIO header pin — inrush current can reset or damage the Pi.
