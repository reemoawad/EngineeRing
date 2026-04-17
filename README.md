# EngineeRing

> **Wearable BLE gesture-input ring with real-time IMU-based cursor control and rehabilitation motion tracking.**  
> Senior Design project — San Diego State University (SDSU) · Software Lead

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python)](https://www.python.org/)
[![BLE](https://img.shields.io/badge/BLE-Nordic%20NUS-informational)](https://infocenter.nordicsemi.com/)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-lightgrey)](https://github.com/reemoawad/EngineeRing)
[![Role](https://img.shields.io/badge/Role-Software%20Lead-green)](https://github.com/reemoawad/EngineeRing)

---

## What It Does

EngineeRing is a wearable smart ring that enables hands-free computer interaction through mid-air hand gestures. A 6-axis IMU (accelerometer + gyroscope) embedded in the ring streams motion data wirelessly over Bluetooth Low Energy to a Python host application. The host performs real-time sensor fusion, gesture classification, and OS-level input injection — allowing users to navigate, click, type, and control presentations without touching a keyboard or mouse.

The system also runs a continuous rehabilitation tracking layer. Every session silently captures 6-DoF motion metrics, exports a structured JSON report, and generates a Range-of-Motion vs. Time plot — designed for physical therapy monitoring and motor recovery analytics.

---

## System Architecture

```
┌──────────────────┐     BLE / NUS      ┌─────────────────────────────────────────────────────────┐
│   Ring Hardware  │  14 bytes @ ~100Hz │                   Python Host Application                │
│                  │ ──────────────────>│                                                          │
│  6-axis IMU      │                    │  BLE Parser → Complementary Filter → Tilt Angles        │
│  (Accel + Gyro)  │                    │      │                                                   │
│  2x Buttons      │                    │      ▼                                                   │
│  nRF52 / equiv.  │                    │  Exponential Smoother (jitter reduction, <15ms lag)      │
└──────────────────┘                    │      │                                                   │
                                        │      ▼                                                   │
                                        │  Gesture FSM (16 gestures × 3 modes)                   │
                                        │      │                                                   │
                                        │      ├──► Cursor Navigation  → PyAutoGUI (OS input)     │
                                        │      ├──► Gesture Typing     → Keystroke injection       │
                                        │      ├──► Presentation Mode  → Slide control            │
                                        │      └──► Rehab Tracking     → JSON + ROM plot export   │
                                        │                                                          │
                                        │  HUD Overlay (Tkinter) — live IMU / mode / status       │
                                        └─────────────────────────────────────────────────────────┘
```

---

## Hardware

| Component | Specification | Notes |
|-----------|--------------|-------|
| IMU | 6-axis (3-axis accel + 3-axis gyro) | Streams accel (ax, ay, az) + gyro (gx, gy, gz) |
| Microcontroller | BLE-capable MCU (nRF52-series or equiv.) | Advertises Nordic UART Service (NUS) |
| Buttons | 2× onboard tactile buttons | Left-click / right-click mappings |
| Wireless | Bluetooth Low Energy 4.2+ | NUS UUID: `6e400001-b5a3-f393-e0a9-e50e24dcca9e` |
| Packet Format | 14 bytes per frame | 2 button bytes + 6× int16 big-endian IMU values |
| Sample Rate | ~100 Hz | Tunable via BLE connection interval |

---

## Signal Processing Pipeline

1. **BLE receive** — `bleak` async loop decodes 14-byte NUS notify packets into (buttons, ax, ay, az, gx, gy, gz)
2. **Complementary filter** — fuses accel + gyro to compute stable pitch/roll/yaw; eliminates gyro drift
3. **Bias correction** — gravity calibration on startup zeros out static tilt offset
4. **Exponential smoothing** — low-pass filter on tilt angles removes jitter; keeps perceived latency <15 ms
5. **Tilt-to-velocity mapping** — filtered pitch/roll mapped to cursor velocity with configurable sensitivity and dead-zones
6. **Gesture FSM** — button state transitions + timing windows classify 16 distinct gestures across 3 interaction modes

---

## Features

- **Wireless BLE** — Nordic UART Service (NUS); no drivers required on host
- **4 operating modes** — Universal (global), Regular, Typing, and Presentation
  - 16 distinct gestures mapped across all modes (clicks, scroll, zoom, calibration, and more)
  - Dynamic mode switching via button gestures; auto-detection of presentation apps
- **Interactive gravity calibration** — press `c` or use a two-button gesture to re-zero
- **HUD overlay** — lightweight Tkinter heads-up display showing connection status, mode, and live IMU data
- **Inactivity timeout** — auto-standby after configurable period to reduce power draw
- **Presentation Mode** — auto-activates when Google Slides or PowerPoint is the foreground window
- **Rehabilitation tracking** — continuous background session capture with JSON export and ROM plot generation

---

## Gesture Reference

### Universal Gestures (all modes)

| # | Gesture | Action |
|---|---------|--------|
| 1 | Hold both buttons 5 s | Exit EngineeRing |
| 2 | Click both buttons | Calibrate |
| 3 | Hold both buttons 2 s | Toggle HUD |
| 4 | Single right button | Right-click |

### Regular Mode

| # | Gesture | Action |
|---|---------|--------|
| 5 | Tilt hand | Move cursor |
| 6 | Single left button | Left-click |
| 7 | Double-click left | Double-click |
| 8 | Hold left + tilt | Click-drag |
| 9 | Hold right + tilt | Scroll |
| 10 | Hold right + left-click | Zoom |

### Typing Mode

| # | Gesture | Action |
|---|---------|--------|
| 11 | Left-click | Space |
| 12 | Right-click | Backspace |
| 13 | Tilt left/right | Navigate letters |
| 14 | Hold left | Confirm character |

### Presentation Mode

| # | Gesture | Action |
|---|---------|--------|
| 15 | Left-click | Next slide |
| 16 | Right-click | Previous slide |

---

## Rehabilitation Tracking

The system silently captures 6-DoF motion data throughout every session. When the session ends, it exports:

- **JSON report** — timestamped session data with the following metrics:

| Metric | Description |
|--------|-------------|
| `peak_rom_deg` | Peak range of motion (degrees) |
| `mean_rom_deg` | Mean range of motion per rep (degrees) |
| `avg_ang_vel_deg_s` | Average angular velocity (°/s) |
| `max_ang_vel_deg_s` | Peak angular velocity (°/s) |
| `estimated_reps` | Estimated discrete wrist movement repetitions |
| `smoothness_index` | Movement smoothness (lower = smoother) |
| `jerk_index` | Jerk magnitude (lower = more controlled) |
| `tremor_index` | High-frequency oscillation level (lower = less tremor) |
| `active_usage_s` | Total seconds of detected active motion |
| `active_usage_fraction` | Fraction of session in active motion (0–1) |
| `rom_variability_std_deg` | Standard deviation of ROM across reps (degrees) |

- **ROM plot** — `matplotlib` PNG: Range of Motion vs. Time for the session

These outputs are designed to feed into physical therapy dashboards, progress-tracking apps, or clinical motion analytics pipelines.

---

## Performance Characteristics

| Metric | Value | Notes |
|--------|-------|-------|
| BLE packet rate | ~100 Hz | Configurable; limited by BLE connection interval |
| Perceived input latency | <15 ms | After complementary filter + smoother |
| Gesture classes | 16 | Across 3 interaction modes |
| Tracked DoF | 6 | Pitch, roll, yaw + 3-axis acceleration |
| Supported platforms | macOS, Windows | Linux partial support via `bleak` |
| Packet size | 14 bytes/frame | 2 button + 6× int16 IMU values |

---

## Software Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| BLE Communication | `bleak` (async) | BLE scan, connect, NUS notify handler |
| Mouse / Keyboard | `pyautogui`, `pynput` | OS-level cursor and keystroke injection |
| Signal Processing | `numpy` | Complementary filter, smoothing, gesture math |
| Rehab Visualization | `matplotlib` | ROM vs. Time session plot generation |
| HUD Overlay | `tkinter` | Live status display (mode, IMU, connection) |
| App Detection | `pygetwindow` (optional) | Presentation mode auto-activation |

---

## Project Structure

```
EngineeRing/
├── Final Code.py          # Main application: gesture engine, HUD, BLE orchestration
├── ring_ble_input.py      # BLE background thread: scan, connect, packet decode
├── rehab_tracker.py       # Session metrics capture and JSON/PNG export
├── requirements.txt       # Python dependencies
└── README.md
```

---

## Setup & Installation

**Requirements:** Python 3.9+, a BLE-enabled computer, and the EngineeRing ring hardware.

```bash
git clone https://github.com/reemoawad/EngineeRing.git
cd EngineeRing
pip install bleak pyautogui pynput numpy pygetwindow matplotlib
python "Final Code.py"
```

The app will scan for a BLE device whose name contains `"EngineeRing"`, connect automatically, and start the gesture engine.

**Key configuration constants** (top of `Final Code.py`):

| Constant | Default | Description |
|----------|---------|-------------|
| `SENSITIVITY` | `1.5` | Cursor speed multiplier |
| `DEAD_ZONE_DEG` | `3.0` | Min tilt angle to register motion (degrees) |
| `SMOOTH_FACTOR` | `0.25` | Exponential smoothing weight (0–1) |
| `INACTIVITY_TIMEOUT_S` | `60` | Seconds before auto-standby |
| `BLE_NAME_CONTAINS` | `"EngineeRing"` | BLE device name filter for scan |

**Hotkeys:**

| Key | Action |
|-----|--------|
| `c` | Re-calibrate gravity / bias |
| `r` | Re-center cursor and zero filters |
| `q` | Quit the application |

---

## How It Works

`ring_ble_input.py` runs a background thread with its own asyncio event loop. It scans for a BLE device advertising the NUS service UUID, connects via `bleak`, and pushes decoded IMU + button packets into a thread-safe deque.

`Final Code.py` polls that deque at ~100 Hz, applies the complementary filter and exponential smoother, maps the filtered tilt vector to screen-space velocity, and calls `pyautogui` to move the cursor or fire input events. Gesture detection uses timing windows and button-state transitions to classify all 16 gestures across modes. App-context detection checks the active window title to auto-switch into Presentation Mode. The rehab tracker captures a snapshot on every polling cycle and writes the JSON report and ROM plot when the session ends.

---

## Real-World Use Cases

- **Accessibility** — hands-free computer navigation for users with limited dexterity or mobility impairments
- **Physical therapy** — range-of-motion tracking and session analytics for wrist/hand motor recovery
- **Presentation control** — wireless slide navigation with no extra hardware or Bluetooth dongles
- **Wearable HCI research** — testbed for gesture-based input, sensor fusion algorithms, and low-latency BLE pipelines

---

## Resume Summary

> *Engineered firmware + Python host software for a wearable BLE gesture-input ring — 6-axis IMU with complementary filter sensor fusion, 16-gesture FSM across 3 interaction modes at ~100 Hz, and rehabilitation session tracking with structured JSON export; served as Software Lead on a cross-functional senior design team.*

---

## License

This project was developed as a Senior Design capstone at San Diego State University.
