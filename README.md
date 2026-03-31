# EngineeRing

Real-time BLE gesture-control ring — wearable IMU-based cursor control and OS input via Python. Senior Design project at San Diego State University (SDSU).

---

## Overview

EngineeRing is a wearable smart ring that lets you control your computer using hand gestures. The ring streams IMU (accelerometer + gyroscope) data and button states over Bluetooth Low Energy (BLE) using the Nordic UART Service (NUS) protocol. A Python host application receives the data, filters it, and translates motion into cursor movement, clicks, scrolling, zoom, and presentation controls — all without touching a keyboard or mouse.

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
- **Cross-platform** — runs on macOS and Windows (Linux untested)

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
- [matplotlib](https://matplotlib.org/) *(optional)* — live data graphing

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
3. **Gesture detection** uses timing windows and button-state transitions to distinguish single-click, double-click, right-click, and long-press (zoom) gestures.
4. **App-context detection** checks the active window on macOS (via AppleScript) or Windows (via `pygetwindow`) to automatically enable Presentation mode when PowerPoint or Google Slides is in focus.

---

## Authors

- **Reemo Awad** — SDSU Senior Design, Electrical Engineering
