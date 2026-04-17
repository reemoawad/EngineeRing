# EngineeRing

> **Real-time BLE gesture-control ring** — wearable IMU-based cursor control and OS input via Python.
> > Senior Design project at San Diego State University (SDSU).
> >
> > ![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python)
> > ![BLE](https://img.shields.io/badge/Protocol-BLE%20%2F%20NUS-brightgreen)
> > ![IMU](https://img.shields.io/badge/Sensor-6--Axis%20IMU-orange)
> > ![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-lightgrey)
> > ![Status](https://img.shields.io/badge/Status-Active-success)
> >
> > ---
> > 
## What Is EngineeRing?

EngineeRing is a **custom-built wearable smart ring** that lets you control your computer hands-free using wrist gestures. It is designed for two real-world use cases:

- **Accessibility & productivity** — replaces the mouse/keyboard for users with limited mobility or repetitive-strain injuries
- - **Rehabilitation monitoring** — passively tracks wrist range of motion, angular velocity, and fatigue metrics during every session, making it a low-cost physiotherapy aid
 
  - The ring streams **6-axis IMU data** (accelerometer + gyroscope) and button states over **Bluetooth Low Energy (BLE)** using the Nordic UART Service (NUS) protocol. A Python host application receives the data, filters it, and translates motion into cursor movement, clicks, scrolling, zoom, and presentation controls — all without touching a keyboard or mouse.
 
  - ---

  ## System Architecture

  ```
  ┌─────────────────────────────────────────────────────────────────────┐
  │                         HARDWARE (Ring)                             │
  │                                                                     │
  │   ┌──────────────┐    ┌─────────────────┐    ┌──────────────────┐  │
  │   │  6-Axis IMU  │───▶│  Microcontroller│───▶│  BLE Transceiver │  │
  │   │  (Accel+Gyro)│    │  (nRF / similar)│    │  Nordic NUS      │  │
  │   └──────────────┘    └─────────────────┘    └────────┬─────────┘  │
  │   ┌──────────────┐                                    │             │
  │   │  2x Buttons  │───▶────────────────────────────────┘             │
  │   └──────────────┘         14-byte BLE packet                       │
  └────────────────────────────────────────────────────────────────────-┘
                                     │ Bluetooth Low Energy
                                                                        ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │                    SOFTWARE HOST (Python)                            │
  │                                                                     │
  │   ring_ble_input.py          Final Code.py                          │
  │   ┌──────────────┐    ┌──────────────────────────────────────────┐  │
  │   │  BLE Driver  │───▶│  IMU Signal Processing                   │  │
  │   │  (bleak)     │    │  • Low-pass filter (α = 0.18)            │  │
  │   │  ~100 Hz     │    │  • Gravity bias removal                  │  │
  │   │  polling     │    │  • Tilt → screen-space velocity mapping  │  │
  │   └──────────────┘    └──────────────────┬───────────────────────┘  │
  │                                          │                           │
  │                          ┌───────────────▼───────────────────────┐  │
  │                          │       Gesture Engine                  │  │
  │                          │  16 gestures × 3 modes (timing FSM)  │  │
  │                          └───────────────┬───────────────────────┘  │
  │                                          │                           │
  │              ┌───────────────────────────┼──────────────────────┐   │
  │              ▼                           ▼                       ▼   │
  │   ┌─────────────────┐     ┌──────────────────────┐  ┌────────────┐  │
  │   │  OS Input Layer │     │  HUD Overlay (Tkinter)│  │   Rehab    │  │
  │   │  (pyautogui /   │     │  Live IMU data, mode, │  │  Tracker   │  │
  │   │   pynput)       │     │  notifications        │  │  (passive) │  │
  │   └─────────────────┘     └──────────────────────┘  └─────┬──────┘  │
  │                                                            │         │
  │                                               ┌────────────▼──────┐  │
  │                                               │  Session Report   │  │
  │                                               │  JSON + ROM graph │  │
  │                                               │  (matplotlib)     │  │
  │                                               └───────────────────┘  │
  └─────────────────────────────────────────────────────────────────────┘
  ```

  ### Data Flow Summary

  ```
  IMU Sensor ──▶ BLE (NUS, 14 bytes @ ~100 Hz) ──▶ Python BLE Driver
      ──▶ Low-Pass Filter + Gravity Removal ──▶ Gesture FSM
      ──▶ OS Cursor / Click Events   +   HUD Overlay   +   Rehab Metrics
      ──▶ Session End: JSON Report + Range-of-Motion PNG Graph
  ```

  ---

  ## Hardware Specification

  | Component | Detail |
  |-----------|--------|
  | Sensor | 6-axis IMU: 3-axis accelerometer + 3-axis gyroscope |
  | Interface | Bluetooth Low Energy (BLE 4.x / 5.x) |
  | Protocol | Nordic UART Service (NUS) UUID `6e400001-b5a3-f393-e0a9-e50e24dcca9e` |
  | Packet format | 2 button bytes + 6 × int16 big-endian (ax, ay, az, gx, gy, gz) = **14 bytes total** |
  | Buttons | 2 onboard tactile buttons (left-click / right-click) |
  | BLE polling rate | ~100 Hz |

  ---

  ## Software Stack

  | Layer | Technology | Purpose |
  |-------|-----------|---------|
  | BLE driver | `bleak` (Python) | Scan, connect, stream IMU packets |
  | Signal processing | `numpy` | Low-pass filter, gravity removal, tilt mapping |
  | OS input | `pyautogui`, `pynput` | Cursor movement, clicks, scroll, keyboard |
  | UI overlay | `tkinter` | Live HUD display |
  | Data visualization | `matplotlib` | ROM vs. Time session graphs |
  | App-context detection | AppleScript (macOS), `pygetwindow` (Windows) | Auto-switch to Presentation mode |

  ---

  ## Real-World Use Cases

  ### 1. Accessibility & Motor-Impairment Aid
  Users with repetitive-strain injuries, tremors, or limited hand mobility can control a computer entirely through wrist tilt and two buttons — no keyboard or mouse required. Inspired by commercial smart rings (Oura Ring, Samsung Galaxy Ring) and wearable HCI research.

  ### 2. Post-Injury Rehabilitation Monitoring
  Physical therapists can use the ring to quantitatively track a patient's wrist recovery between clinic visits. The passive rehab tracker records every session's range of motion, angular velocity, smoothness, and fatigue patterns — automatically, with no extra setup.

  ### 3. Hands-Free Presentation Control
  Automatic detection of Google Slides and PowerPoint switches the ring into Presentation mode, turning it into a wireless clicker and laser-pointer controller — useful for surgeons, lab instructors, or anyone presenting with gloves on.

  ---

  ## Signal Processing Pipeline

  Raw IMU data goes through the following processing chain before becoming cursor movement:

  1. **BLE packet decode** — 14-byte packet split into 2 button states + 6 int16 IMU values (ax, ay, az, gx, gy, gz)
  2. 2. **Gravity bias removal** — static gravity vector subtracted using a calibration baseline captured at session start (or on demand via `c`)
     3. 3. **Low-pass filter** — exponential moving average applied: `filtered = α × raw + (1 − α) × prev` with `α = SMOOTHING = 0.18`
        4. 4. **Dead-zone gating** — tilt vectors below `DEADZONE = 0.04 rad` are zeroed out to prevent cursor drift from micro-tremors
           5. 5. **Velocity mapping** — filtered tilt magnitude multiplied by `SENSITIVITY = 1800` and clamped to screen bounds
              6. 6. **Gesture FSM** — button timing windows (single click, double click, hold) and button combinations are evaluated to identify one of 16 gestures
                
                 7. ---
                
                 8. ## Sample Rehabilitation Metrics
                
                 9. Below is an example of the JSON report automatically saved at the end of a session:
                
                 10. ```json
                     {
                       "session_duration_s": 312.4,
                       "active_usage_s": 198.7,
                       "active_usage_fraction": 0.636,
                       "avg_rom_deg": 34.2,
                       "max_rom_deg": 61.8,
                       "avg_ang_vel_deg_s": 87.3,
                       "max_ang_vel_deg_s": 204.6,
                       "estimated_reps": 142,
                       "smoothness_index": 0.041,
                       "jerk_index": 0.018,
                       "tremor_index": 0.007,
                       "rom_variability_std_deg": 8.1,
                       "typed_letters": 237,
                       "typed_letters_per_min": 45.5,
                       "rom_drop_percent": 12.3,
                       "speed_drop_percent": 9.8,
                       "smoothness_change_percent": 4.2
                     }
                     ```

                     The ROM vs. Time graph (`rehab_session_<timestamp>_rom.png`) plots instantaneous range of motion (degrees) over the full session duration, making it easy to identify periods of high activity, fatigue onset, and movement consistency.

                     ---

                     ## Features

                     - **Wireless BLE connectivity** via the Nordic UART Service (NUS)
                     - - **Four operating modes** — Universal (top-level), with Regular, Typing, and Presentation sub-modes
                       - - **16 distinct gestures** — mapped across all modes for clicks, scroll, zoom, calibration, and more
                         - - **Interactive gravity calibration** — press `c` or use the two-button gesture to re-calibrate
                           - - **HUD overlay** — a lightweight Tkinter heads-up display shows connection status, current mode, and live IMU data
                             - - **Blocking and non-blocking notifications** — important alerts pause the app until dismissed; minor status updates appear as unobtrusive overlays
                               - - **Background rehabilitation tracking** — passive motion analytics collected every session with no extra setup
                                 - - **Cross-platform** — runs on macOS and Windows (Linux untested)
                                  
                                   - ---

                                   ## Operating Modes

                                   All functionality is organized under a single **Universal mode** framework. Within it, the app operates in one of three sub-modes at any time, displayed in the HUD overlay.

                                   ```
                                   Universal
                                   ├── Regular          ← default; tilt = cursor, buttons = click
                                   ├── Typing
                                   │   ├── Click-to-Type
                                   │   └── Dwell-to-Type
                                   └── Presentation     ← auto-detected via active window
                                   ```

                                   **Regular Mode** — The default sub-mode. Wrist tilt moves the cursor; button presses fire left- and right-click events. Scroll, zoom, and edge-scroll gestures are all active.

                                   **Typing Mode** — Engaged automatically when keyboard activity is detected, or switched to manually via gesture. Cursor movement is suppressed so normal typing is uninterrupted. Supports two text-entry methods:
                                   - *Click-to-Type* — the user physically clicks a button to register each character input.
                                   - - *Dwell-to-Type* — hovering over a target for a set duration triggers the input automatically, enabling hands-free or reduced-dexterity text entry.
                                    
                                     - **Presentation Mode** — Activated automatically when a supported presentation application is detected as the foreground window. Acts as a wireless clicker and laser-pointer controller.
                                    
                                     - ---

                                     ## Gesture Reference

                                     ### Universal Gestures *(all modes)*

                                     | # | Gesture | Purpose |
                                     |---|---------|---------|
                                     | 1 | Hold both buttons 5 s | Exit EngineeRing |
                                     | 2 | Click both buttons simultaneously | Calibrate |
                                     | 3 | Hold both buttons 5 s | Disconnect ring |
                                     | 4 | Hold right button 5 s | Manually switch modes |

                                     ### Regular Mode

                                     | # | Gesture | Purpose |
                                     |---|---------|---------|
                                     | 5 | Click | Right click / Left click |
                                     | 6 | Double-click right button | Exit window |
                                     | 7 | Hold right button + tilt | Scroll |
                                     | 8 | Double-click left button | Zoom in |
                                     | 9 | Hold left button | Zoom out |

                                     ### Typing Mode

                                     | # | Gesture | Purpose |
                                     |---|---------|---------|
                                     | 10 | Double-click right button | Toggle Click-to-Type ⇔ Dwell-to-Type |

                                     ### Presentation Mode

                                     | # | Gesture | Purpose |
                                     |---|---------|---------|
                                     | 11 | Left-click | Next slide |
                                     | 12 | Right-click | Previous slide |
                                     | 13 | Double-click right button | Toggle Enter Slideshow |
                                     | 14 | Double-click left button | Toggle Mouse Icon ⇔ Laser |
                                     | 15 | Hold left button 1.5 s | Toggle Annotation Pen ⇔ Regular Mouse |
                                     | 16 | Triple-click left button | Undo annotation |

                                     ---

                                     ## Rehabilitation Metrics

                                     The app passively collects motion analytics throughout every ring session. On session end, two files are saved automatically:

                                     - `rehab_session_<timestamp>.json` — full session metrics report
                                     - - `rehab_session_<timestamp>_rom.png` — Range of Motion vs. Time graph
                                      
                                       - ### Motion Metrics
                                      
                                       - | Metric | Description |
                                       - |--------|-------------|
                                       - | `avg_rom_deg` | Mean range of motion per movement cycle (degrees) |
                                       - | `max_rom_deg` | Peak range of motion recorded in the session (degrees) |
                                       - | `avg_ang_vel_deg_s` | Average angular velocity (degrees/second) |
                                       - | `max_ang_vel_deg_s` | Peak angular velocity (degrees/second) |
                                       - | `estimated_reps` | Estimated number of discrete wrist movement repetitions |
                                       - | `smoothness_index` | Movement smoothness (lower = smoother) |
                                       - | `jerk_index` | Jerk magnitude (lower = more controlled movement) |
                                       - | `tremor_index` | High-frequency oscillation level (lower = less tremor) |
                                       - | `active_usage_s` | Total seconds of detected active motion |
                                       - | `active_usage_fraction` | Fraction of session time spent in active motion (0–1) |
                                       - | `rom_variability_std_deg` | Standard deviation of ROM across reps (degrees) |
                                      
                                       - ### Functional Metrics
                                      
                                       - | Metric | Description |
                                       - |--------|-------------|
                                       - | `typed_letters` | Total keystrokes detected while in Typing mode |
                                       - | `typed_letters_per_min` | Typing rate (characters per minute) |
                                      
                                       - ### Fatigue Metrics *(first half vs. second half comparison)*
                                      
                                       - | Metric | Description |
                                       - |--------|-------------|
                                       - | `rom_drop_percent` | % decrease in average ROM from first to second half |
                                       - | `speed_drop_percent` | % decrease in average angular velocity, first vs. second half |
                                       - | `smoothness_change_percent` | % change in smoothness index, first vs. second half |
                                      
                                       - ---

                                       ## HUD Visual Feedback

                                       A persistent heads-up display (HUD) rendered via Tkinter sits in the corner of the screen throughout the session. It shows:

                                       - **Connection status** — connected, scanning, or disconnected
                                       - - **Current mode** — which sub-mode is active (Regular, Typing, or Presentation)
                                         - - **Live IMU data** — real-time accelerometer and gyroscope readings
                                           - - **Active notifications** — non-blocking status messages that appear and fade automatically
                                             - - **Session info** — elapsed session time and active usage indicator
                                              
                                               - ---

                                               ## Project Structure

                                               ```
                                               EngineeRing/
                                               ├── firmware/                  # Ring firmware (nRF-based BLE firmware)
                                               ├── software/
                                               │   ├── Final Code.py          # Main application: gesture engine, HUD, BLE orchestration
                                               │   └── ring_ble_input.py      # BLE driver — scans, connects, and streams IMU packets
                                               └── README.md
                                               ```

                                               ---

                                               ## Requirements

                                               - Python 3.9+
                                               - - `bleak` — cross-platform BLE library
                                                 - - `pyautogui` — mouse/keyboard control
                                                   - - `pynput` — low-level keyboard listener
                                                     - - `numpy` — IMU signal processing
                                                       - - `pygetwindow` *(optional, Windows/Linux)* — active-window detection
                                                         - - `matplotlib` *(optional)* — live data graphing and rehab session plots
                                                          
                                                           - ```bash
                                                             pip install bleak pyautogui pynput numpy pygetwindow matplotlib
                                                             ```

                                                             ---

                                                             ## Usage

                                                             1. Power on the ring and ensure BLE is enabled on your computer.
                                                             2. 2. Edit the configuration block near the top of `Final Code.py` if needed:
                                                                3.    - Set `BLE_NAME_CONTAINS` to match your ring's advertised name (default: `"EngineeRing"`).
                                                                      -    - Optionally hard-code `BLE_ADDRESS` to skip scanning.
                                                                           - 3. Run the main script:
                                                                            
                                                                             4. ```bash
                                                                                python "Final Code.py"
                                                                                ```

                                                                                The script will scan for the ring, connect, and launch the HUD overlay. Tilt your wrist to move the cursor. Use the ring buttons to click.

                                                                                ### Hotkeys

                                                                                | Key | Action |
                                                                                |-----|--------|
                                                                                | `c` | Re-calibrate gravity / bias |
                                                                                | `r` | Re-center cursor and zero filters |
                                                                                | `q` | Quit the application |

                                                                                ---

                                                                                ## Configuration

                                                                                Key tuning constants defined at the top of `Final Code.py`:

                                                                                | Constant | Default | Description |
                                                                                |----------|---------|-------------|
                                                                                | `SENSITIVITY` | `1800` | Cursor speed multiplier |
                                                                                | `DEADZONE` | `0.04` | Minimum tilt to register movement |
                                                                                | `SMOOTHING` | `0.18` | Low-pass filter strength (0 = none, 1 = max) |
                                                                                | `SCROLL_SENSITIVITY` | `18` | Scroll speed |
                                                                                | `USE_BLE` | `True` | True for BLE, False for serial |
                                                                                | `BLE_NAME_CONTAINS` | `"EngineeRing"` | Partial BLE device name to scan for |

                                                                                ---

                                                                                ## Authors

                                                                                Reem Awad, Will Craychee, Roman Guerrero, Anna Leonhardt, Jeriah Navarro
                                                                                San Diego State University — Senior Design Project
