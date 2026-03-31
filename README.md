# EngineeRing

Real-time BLE gesture-control ring — wearable IMU-based cursor control and OS input via Python. Senior Design project at San Diego State University (SDSU).

---

## Overview

EngineeRing is a wearable smart ring that lets you control your computer using hand gestures. The ring streams IMU (accelerometer + gyroscope) data and button states over Bluetooth Low Energy (BLE) using the Nordic UART Service (NUS) protocol. A Python host application receives the data, filters it, and translates motion into cursor movement, clicks, scrolling, zoom, and presentation controls — all without touching a keyboard or mouse.

In the background, the app silently tracks rehabilitation metrics for every session. When the session ends, it automatically saves a JSON report and generates a Range of Motion vs. Time PNG graph.

---

## Features

- **Wireless BLE connectivity** via the Nordic UART Service (NUS)
- **Four operating modes** — Universal (top-level), with Regular, Typing, and Presentation sub-modes
- **16 distinct gestures** — mapped across all modes for clicks, scroll, zoom, calibration, and more
- **Interactive gravity calibration** — press `c` or use the two-button gesture to re-calibrate
- **HUD overlay** — a lightweight Tkinter heads-up display shows connection status, current mode, and live IMU data
- **Blocking and non-blocking notifications** — important alerts pause the app until dismissed; minor status updates appear as unobtrusive overlays
- **Background rehabilitation tracking** — passive motion analytics collected every session with no extra setup
- **Cross-platform** — runs on macOS and Windows (Linux untested)

---

## Operating Modes

All functionality is organized under a single **Universal mode** framework. Within it, the app operates in one of three sub-modes at any time, displayed in the HUD overlay.

```
Universal
├── Regular
├── Typing
│   ├── Click-to-Type
│   └── Dwell-to-Type
└── Presentation
```

### Regular Mode

The default sub-mode. Wrist tilt moves the cursor; button presses fire left- and right-click events. Scroll, zoom, and edge-scroll gestures are all active.

### Typing Mode

Engaged automatically when keyboard activity is detected, or switched to manually via gesture. Cursor movement is suppressed so normal typing is uninterrupted. Typing mode supports two text-entry methods:

- **Click-to-Type** — the user physically clicks a button to register each character input. Prioritizes deliberate, precise input.
- **Dwell-to-Type** — hovering over a target for a set duration triggers the input automatically, enabling hands-free or reduced-dexterity text entry.

The ring returns to Regular mode after a short period of inactivity.

### Presentation Mode

Activated automatically when a supported presentation application is detected as the foreground window. In this mode the ring acts as a wireless clicker and laser-pointer controller.

- **Google Slides** — detected via active Chrome tab URL (macOS AppleScript or equivalent)
- **Microsoft PowerPoint** — detected via active window title on macOS and Windows

---

## Gesture Reference

### Universal Gestures

These gestures are available in all modes.

| # | Gesture | Purpose |
|---|---------|---------|
| 1 | Hold both buttons for 5 seconds | Exit EngineeRing |
| 2 | Click both buttons at the same time | Calibrate |
| 3 | Hold both buttons for 5 seconds | Disconnect ring from connected device |
| 4 | Hold right-click button for 5 seconds | Manually switch modes |

### Regular Mode Gestures

| # | Gesture | Purpose |
|---|---------|---------|
| 5 | Click | Right click / Left click |
| 6 | Double-click right-click button | Exit window |
| 7 | Hold right-click button, hover in desired scroll direction | Scroll |
| 8 | Double-click left-click button | Zoom in |
| 9 | Hold left button | Zoom out |

### Typing Mode Gestures

| # | Gesture | Purpose |
|---|---------|---------|
| 10 | Double-click right-click | Toggle Click-to-Type ⇔ Dwell-to-Type |

### Presentation Mode Gestures

| # | Gesture | Purpose |
|---|---------|---------|
| 11 | Left-click | Next slide |
| 12 | Right-click | Previous slide |
| 13 | Double-click right-click | Toggle Enter Slideshow |
| 14 | Double-click left-click | Toggle Mouse Icon ⇔ Laser |
| 15 | Hold left-click for 1.5 seconds | Toggle Annotation Pen ⇔ Regular Mouse |
| 16 | Triple-click left-click | Undo annotation |

---

## Rehabilitation Metrics

The app passively collects motion analytics throughout every ring session with no configuration required. When the session ends (pressing `q` or closing the window), two output files are automatically saved to the working directory:

- **`rehab_session_<timestamp>.json`** — full session metrics report
- **`rehab_session_<timestamp>_rom.png`** — Range of Motion vs. Time graph for the session

The ROM vs. Time graph is generated using `matplotlib`, plotting instantaneous range of motion (degrees) over the full session duration. It makes it easy to visually identify periods of high activity, fatigue onset, and consistency of movement across a therapy session.

A summary of the session metrics is also displayed directly to the user in the terminal and HUD at session end.

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

## HUD Visual Feedback

A persistent heads-up display (HUD) rendered via Tkinter sits in the corner of the screen throughout the session. It provides at-a-glance feedback without interrupting the user's workflow.

The HUD shows:

- **Connection status** — whether the ring is connected, scanning, or disconnected
- **Current mode** — which sub-mode is active (Regular, Typing, or Presentation)
- **Live IMU data** — real-time accelerometer and gyroscope readings
- **Active notifications** — non-blocking status messages that appear and fade automatically
- **Session info** — elapsed session time and active usage indicator

The HUD is designed to be unobtrusive and stays on top of other windows so it is always visible.

---

## Blocking and Non-Blocking Notifications

The app uses two distinct notification styles depending on the urgency and nature of the message.

### Blocking Notifications

Blocking notifications are modal dialogs that pause the application and require the user to acknowledge them before proceeding. They are used for situations where the user must be informed and the app cannot safely continue without a response.

Examples of blocking notifications:

- BLE connection failure — ring not found after scanning
- Calibration required before the session can begin
- Critical IMU data error or packet loss
- Session save failure (could not write JSON or PNG to disk)

### Non-Blocking Notifications

Non-blocking notifications appear as brief overlay messages in the HUD and fade automatically after a few seconds. They inform the user of routine status changes without interrupting their workflow.

Examples of non-blocking notifications:

- Mode switch (e.g., "Switched to Typing mode")
- Successful BLE reconnect after brief dropout
- Calibration complete
- Rehab metrics saved successfully at session end
- Low activity warning during a therapy session

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

## How It Works

1. **`ring_ble_input.py`** runs a background thread with its own asyncio event loop. It scans for a BLE device advertising the NUS service, connects via `bleak`, and pushes decoded IMU + button packets into a thread-safe deque.
2. **`Final Code.py`** polls that deque at ~100 Hz, applies a low-pass filter, maps the filtered tilt vector to screen-space velocity, and calls `pyautogui` to move the cursor or fire input events.
3. **Gesture detection** uses timing windows and button-state transitions to distinguish all 16 gestures across modes.
4. **App-context detection** checks the active window on macOS (via AppleScript) or Windows (via `pygetwindow`) to automatically switch between Regular and Presentation sub-modes.
5. **Rehab tracking** runs silently in the background on every frame. On session end, the collected IMU time-series is processed to compute all motion, functional, and fatigue metrics, which are written to a JSON file and a ROM vs. Time PNG graph.

---

## Authors

- **Reem Awad**, **Will Craychee**, **Roman Guerrero**, **Anna Leonhardt**, **Jeriah Navarro**
