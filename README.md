# EngineeRing

Real-time BLE gesture-control ring — wearable IMU-based cursor control and OS input via Python. Senior Design project at San Diego State University (SDSU).

---

## Overview

EngineeRing is a wearable smart ring that lets you control your computer using hand gestures. The ring streams IMU (accelerometer + gyroscope) data and button states over Bluetooth Low Energy (BLE) using the Nordic UART Service (NUS) protocol. A Python host application receives the data, filters it, and translates motion into cursor movement, clicks, scrolling, zoom, and presentation controls — all without touching a keyboard or mouse.

In the background, the app silently tracks rehabilitation metrics for every session. When the session ends, it automatically saves a JSON report and generates a Range of Motion vs. Time PNG graph.

---

## Features

- **Wireless BLE connectivity** via the Nordic UART Service (NUS)
- **Real-time cursor control** driven by wrist tilt (accelerometer/gyroscope fusion)
- **Gesture recognition** — left-click, right-click, double-click, and long-press
- **Scroll mode** — tilt the ring to scroll pages up, down, left, or right
- **Zoom** — long-press + tilt or triple-tap SPACE to zoom in/out
- **Presentation mode** — auto-detected for PowerPoint and Google Slides; use the ring as a clicker/laser pointer
- **Typing mode** — temporarily suspends cursor control so you can type normally
- **Interactive gravity calibration** — press `c` to re-calibrate the gravity/bias baseline
- **Cursor re-center** — press `r` to snap the cursor back to center and zero the filters
- **HUD overlay** — a lightweight Tkinter heads-up display shows connection status, current mode, and live IMU data
- **Background rehabilitation tracking** — passive motion analytics collected every session with no extra setup
- **Cross-platform** — runs on macOS and Windows (Linux untested)

---

## Operating Modes

The ring operates in one of three modes at any time, shown in the HUD overlay:

**Regular mode** is the default. Wrist tilt moves the cursor; button presses fire left- and right-click events. Scroll, zoom, and edge-scroll gestures are all active.

**Typing mode** is engaged automatically when keyboard activity is detected. Cursor movement is suppressed so normal typing is uninterrupted. The ring resumes Regular mode after a short period of inactivity.

**Presentation mode** is activated automatically when PowerPoint or Google Slides is the foreground application (detected via AppleScript on macOS or `pygetwindow` on Windows). In this mode the ring acts as a wireless clicker and laser-pointer controller — button 1 advances slides, button 2 goes back, and a long-press toggles the laser pointer effect.

---

## Hardware

- Custom BLE ring with an IMU (6-axis: 3-axis accelerometer + 3-axis gyroscope)
- Two onboard buttons (left-click / right-click)
- Firmware advertises the Nordic UART Service UUID: `6e400001-b5a3-f393-e0a9-e50e24dcca9e`
- BLE packet format: `2 button bytes + 6 x int16 big-endian (ax, ay, az, gx, gy, gz)` = 14 bytes total

---

## Project Structure

```
EngineeRing/
├── Final Code.py        # Main application: gesture engine, HUD, BLE orchestration
├── ring_ble_input.py    # BLE driver — scans, connects, and streams IMU packets
└── README.md
```

---

## Requirements

- Python 3.9+
- [bleak](https://github.com/hbldh/bleak) — cross-platform BLE library
- [pyautogui](https://github.com/asweigart/pyautogui) — mouse/keyboard control
- [pynput](https://github.com/moses-palmer/pynput) — low-level keyboard listener
- [numpy](https://numpy.org/) — IMU signal processing
- [pygetwindow](https://github.com/asweigart/PyGetWindow) *(optional, Windows/Linux)* — active-window detection
- [matplotlib](https://matplotlib.org/) *(optional)* — live data graphing and rehab session plots

Install dependencies:

```bash
pip install bleak pyautogui pynput numpy pygetwindow matplotlib
```

---

## Usage

1. Power on the ring and ensure BLE is enabled on your computer.
2. Edit the configuration block near the top of `Final Code.py` if needed:
   - Set `BLE_NAME_CONTAINS` to match your ring's advertised name (default: `"EngineeRing"`).
   - Optionally hard-code `BLE_ADDRESS` to skip scanning.
3. Run the main script:

```bash
python "Final Code.py"
```

4. The script will scan for the ring, connect, and launch the HUD overlay.
5. Tilt your wrist to move the cursor. Use the ring buttons to click.

### Hotkeys

| Key | Action |
|-----|--------|
| `c` | Re-calibrate gravity / bias |
| `r` | Re-center cursor and zero filters |
| `q` | Quit the application |

---

## Configuration

Key tuning constants are defined at the top of `Final Code.py`:

| Constant | Default | Description |
|----------|---------|-------------|
| `SENSITIVITY` | `1800` | Cursor speed multiplier |
| `DEADZONE` | `0.04` | Minimum tilt to register movement |
| `SMOOTHING` | `0.18` | Low-pass filter strength (0 = none, 1 = max) |
| `SCROLL_SENSITIVITY` | `18` | Scroll speed |
| `USE_BLE` | `True` | `True` for BLE, `False` for serial |
| `BLE_NAME_CONTAINS` | `"EngineeRing"` | Partial BLE device name to scan for |

---

## Rehabilitation Metrics

The app passively collects motion analytics throughout every ring session with no configuration required. When the session ends (pressing `q` or closing the window), two output files are automatically saved to the working directory:

- **`rehab_session_<timestamp>.json`** — full session metrics report
- **`rehab_session_<timestamp>_rom.png`** — Range of Motion vs. Time graph for the session

### Output Files

#### JSON Report

```json
{
  "session_start_iso": "2025-12-19T12:14:53",
  "session_end_iso": "2025-12-19T12:23:03",
  "duration_s": 489.74,
  "iso_year": 2025,
  "iso_week": 51,
  "motion_metrics": {
    "avg_rom_deg": 29.44,
    "max_rom_deg": 89.99,
    "avg_ang_vel_deg_s": 44.99,
    "max_ang_vel_deg_s": 591.78,
    "estimated_reps": 79,
    "smoothness_index": 0.141,
    "jerk_index": 6.07,
    "tremor_index": 19.57,
    "active_usage_s": 256.21,
    "active_usage_fraction": 0.523,
    "rom_variability_std_deg": 22.74
  },
  "functional_metrics": {
    "typed_letters": 7,
    "typed_letters_per_min": 0.86
  },
  "fatigue_metrics": {
    "rom_drop_percent": 37.08,
    "speed_drop_percent": 44.30,
    "smoothness_change_percent": -52.63
  }
}
```

#### PNG Graph

A ROM vs. Time plot is generated using `matplotlib`, showing the instantaneous range of motion (degrees) sampled over the full session duration. This makes it easy to visually identify periods of high activity, fatigue onset, and consistency of movement across a therapy session.

### Metric Definitions

**Motion metrics** describe the quality and quantity of wrist movement:

| Metric | Description |
|--------|-------------|
| `avg_rom_deg` | Mean range of motion per movement cycle (degrees) |
| `max_rom_deg` | Peak range of motion recorded in the session (degrees) |
| `avg_ang_vel_deg_s` | Average angular velocity (degrees/second) |
| `max_ang_vel_deg_s` | Peak angular velocity (degrees/second) |
| `estimated_reps` | Estimated number of discrete wrist movement repetitions |
| `smoothness_index` | Movement smoothness (lower = smoother) |
| `jerk_index` | Jerk magnitude (lower = more controlled movement) |
| `tremor_index` | High-frequency oscillation level (lower = less tremor) |
| `active_usage_s` | Total seconds of detected active motion |
| `active_usage_fraction` | Fraction of session time spent in active motion (0–1) |
| `rom_variability_std_deg` | Standard deviation of ROM across reps (degrees) |

**Functional metrics** capture computer-interaction activity during the session:

| Metric | Description |
|--------|-------------|
| `typed_letters` | Total keystrokes detected while in Typing mode |
| `typed_letters_per_min` | Typing rate (characters per minute) |

**Fatigue metrics** compare the first and second halves of the session to estimate fatigue:

| Metric | Description |
|--------|-------------|
| `rom_drop_percent` | Percent decrease in average ROM from first to second half |
| `speed_drop_percent` | Percent decrease in average angular velocity, first to second half |
| `smoothness_change_percent` | Percent change in smoothness index, first to second half |

---

## How It Works

1. **`ring_ble_input.py`** runs a background thread with its own asyncio event loop. It scans for a BLE device advertising the NUS service, connects via `bleak`, and pushes decoded IMU + button packets into a thread-safe deque.
2. **`Final Code.py`** polls that deque at ~100 Hz, applies a low-pass filter, maps the filtered tilt vector to screen-space velocity, and calls `pyautogui` to move the cursor or fire input events.
3. **Gesture detection** uses timing windows and button-state transitions to distinguish single-click, double-click, right-click, and long-press (zoom) gestures.
4. **App-context detection** checks the active window on macOS (via AppleScript) or Windows (via `pygetwindow`) to automatically enable Presentation mode when PowerPoint or Google Slides is in focus.
5. **Rehab tracking** runs silently in the background on every frame. On session end, the collected IMU time-series is processed to compute all motion, functional, and fatigue metrics, which are written to a JSON file and a ROM vs. Time PNG graph.

---

## Authors

- **Reemo Awad** — SDSU Senior Design, Electrical Engineering
