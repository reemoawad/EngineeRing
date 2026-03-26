#!/usr/bin/env python3
import re
import time
from collections import deque
import numpy as np
import serial
import pyautogui
from pynput import keyboard
import sys
IS_WINDOWS = sys.platform.startswith("win")
IS_MAC = (sys.platform == "darwin")
from ring_ble_input import RingBLEInput
import math
import os, sys
import subprocess
from urllib.parse import urlparse
import json
import datetime

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None  # graphs are skipped if matplotlib is not installed

try:
    import pygetwindow as gw
except ImportError:
    gw = None  # app detection will be skipped if not available

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if THIS_DIR not in sys.path:
    sys.path.insert(0, THIS_DIR)

import tkinter as tk

class RingHUD:
    def __init__(self, size=170, corner="bottom-right", margin=20):
        self.size = size
        self.corner = corner
        self.margin = margin

        # --- macOS-style colors ---
        self.MAC_BG      = "#F5F5F7"   # light card background
        self.MAC_BORDER  = "#D0D0D5"   # subtle border
        self.MAC_TEXT    = "#111111"   # dark text / arrow
        self.MAC_MUTED   = "#E3E3E8"   # muted / pressed
        self.MAC_ACCENT  = "#007AFF"   # (not used for buttons now)
        self.BANNER_BG   = "#EDEDED"

        # Root HUD window
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.wm_attributes("-alpha", 0.95)

        # Position in corner
        self.root.update_idletasks()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        if corner == "bottom-right":
            x = screen_w - size - margin
            y = screen_h - size - margin
        elif corner == "bottom-left":
            x = margin
            y = screen_h - size - margin
        elif corner == "top-right":
            x = screen_w - size - margin
            y = margin
        else:  # top-left
            x = margin
            y = margin

        self.root.geometry(f"{size}x{size}+{x}+{y}")

        # Canvas where everything is drawn
        self.canvas = tk.Canvas(
            self.root,
            width=size,
            height=size,
            highlightthickness=0,
            bg=self.MAC_BG
        )
        self.canvas.pack()

        # --- Rounded card background ---
        pad = 6
        self._rounded_rect(
            self.canvas,
            pad,
            pad,
            size - pad,
            size - pad,
            radius=18,
            outline=self.MAC_BORDER,
            width=1,
            fill=self.MAC_BG
        )

        self.center = (size // 2, size // 2)

        # Make the main circle big but ensure side circles still fit
        # (tuned so everything stays inside the square)
        self.radius = int(size * 0.36)   # was 0.42 before → slightly smaller

        # Main circle (digital "mouse body")
        self.circle_id = self.canvas.create_oval(
            self.center[0] - self.radius,
            self.center[1] - self.radius,
            self.center[0] + self.radius,
            self.center[1] + self.radius,
            outline=self.MAC_BORDER,
            width=2,
            fill="#FFFFFF"
        )

        # Direction arrow
        self.arrow_id = self.canvas.create_line(
            self.center[0], self.center[1],
            self.center[0], self.center[1],
            arrow=tk.LAST,
            width=3,
            fill=self.MAC_TEXT
        )

        # Left/right button indicators (small circles on each side)
        # Carefully chosen offset so they don't get clipped
        b_r = int(self.radius * 0.32)
        offset = int(self.radius * 0.95)

        self.left_btn_id = self.canvas.create_oval(
            self.center[0] - offset - b_r,
            self.center[1] - b_r,
            self.center[0] - offset + b_r,
            self.center[1] + b_r,
            outline=self.MAC_BORDER,
            width=2,
            fill="#FFFFFF"
        )

        self.right_btn_id = self.canvas.create_oval(
            self.center[0] + offset - b_r,
            self.center[1] - b_r,
            self.center[0] + offset + b_r,
            self.center[1] + b_r,
            outline=self.MAC_BORDER,
            width=2,
            fill="#FFFFFF"
        )

        # Mode label inside circle
        self.mode_text_id = self.canvas.create_text(
            self.center[0],
            self.center[1],
            text="",
            fill=self.MAC_TEXT,
            font=("Helvetica", 12, "bold")
        )

        # --- Top-right toast notification window (rounded) ---
        self.toast_after_id = None
        self.toast = tk.Toplevel(self.root)
        self.toast.overrideredirect(True)
        self.toast.attributes("-topmost", True)

        toast_w = 280
        toast_h = 48
        x_toast = screen_w - toast_w - self.margin
        y_toast = self.margin
        self.toast.geometry(f"{toast_w}x{toast_h}+{x_toast}+{y_toast}")

        self.toast_canvas = tk.Canvas(
            self.toast,
            width=toast_w,
            height=toast_h,
            highlightthickness=0,
            bg=self.MAC_BG
        )
        self.toast_canvas.pack(fill="both", expand=True)

        self._rounded_rect(
            self.toast_canvas,
            1,
            1,
            toast_w - 1,
            toast_h - 1,
            radius=14,
            outline=self.MAC_BORDER,
            width=1,
            fill=self.MAC_BG
        )

        self.toast_label = tk.Label(
            self.toast_canvas,
            text="",
            fg=self.MAC_TEXT,
            bg=self.MAC_BG,
            font=("Helvetica", 10),
            anchor="w",
            padx=14
        )
        self.toast_label.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.toast.withdraw()

        # --- HUD banner area (bottom strip) ---
        self.banner_after_id = None
        pad = 6
        banner_height = 26

        self.banner_bg = self.canvas.create_rectangle(
            pad + 4,
            self.size - banner_height - pad,
            self.size - pad - 4,
            self.size - pad,
            fill=self.BANNER_BG,
            outline=""
        )
        self.banner_text = self.canvas.create_text(
            self.size // 2,
            self.size - banner_height // 2 - pad,
            text="",
            fill=self.MAC_TEXT,
            font=("Helvetica", 9)
        )

        self.canvas.itemconfigure(self.banner_bg, state="hidden")
        self.canvas.itemconfigure(self.banner_text, state="hidden")

    # ---- helpers ----
    def _rounded_rect(self, canvas, x1, y1, x2, y2, radius=12, **kwargs):
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1
        ]
        return canvas.create_polygon(points, smooth=True, **kwargs)

    def pump(self):
        """Run one Tk update cycle (call this every frame from the main loop)."""
        try:
            self.root.update_idletasks()
            self.root.update()
        except tk.TclError:
            # Window was probably closed; ignore so the app doesn't crash
            pass

    def set_mode(self, mode_name: str):
        """Update the mode label (e.g., 'Pointer', 'Typing', 'Present')."""
        self.canvas.itemconfig(self.mode_text_id, text=mode_name)

    def set_buttons(self, left_down: bool, right_down: bool):
        """Visually show which buttons are pressed."""
        pressed_color = self.MAC_BORDER   # same grey as the outline
        idle_color    = "#FFFFFF"

        self.canvas.itemconfig(
            self.left_btn_id,
            fill=pressed_color if left_down else idle_color
        )
        self.canvas.itemconfig(
            self.right_btn_id,
            fill=pressed_color if right_down else idle_color
        )

    def set_direction(self, dx: float, dy: float, threshold: float = 0.05):
        """
        dx, dy: your current velocity or movement vector.
        If magnitude is below threshold, arrow returns to center (no movement).
        """
        mag = (dx ** 2 + dy ** 2) ** 0.5
        if mag < threshold:
            # "no movement" -> arrow shrinks to center
            self.canvas.coords(
                self.arrow_id,
                self.center[0], self.center[1],
                self.center[0], self.center[1]
            )
            return

        # Normalize
        nx = dx / mag
        ny = dy / mag

        # Flip Y if your coordinate system is opposite Tk's
        ny = -ny

        length = self.radius * 0.8
        end_x = self.center[0] + nx * length
        end_y = self.center[1] + ny * length

        self.canvas.coords(
            self.arrow_id,
            self.center[0], self.center[1],
            end_x, end_y
        )

def notify(message: str, title: str = "EngineeRing", blocking: bool = False):
    """
    Show a message to the user.

    - blocking=False → Notification Center banner (auto-disappears, non-blocking)
    - blocking=True  → big popup with OK button (display alert)

    IMPORTANT: we send AppleScript ASYNCHRONOUSLY so the main loop
    (ring → mouse) never pauses. You can still move/click with the ring
    while the alert is on screen.
    """
    # Always log to terminal
    print(message)

    if sys.platform != "darwin":
        return  # Only macOS uses osascript here

    # Clean up the message for AppleScript
    safe_msg = message.replace('"', '\\"').replace("\n", " ")
    safe_title = title.replace('"', '\\"')

    if blocking:
        # Modal-style alert that auto-dismisses after ALERT_TIMEOUT_S seconds
        script = (
            f'display alert "{safe_title}" '
            f'message "{safe_msg}" '
            f'giving up after {ALERT_TIMEOUT_S}'
        )
    else:
        # Non-blocking Notification Center banner
        script = f'display notification "{safe_msg}" with title "{safe_title}"'

    try:
        # Fire-and-forget so your IMU loop keeps running
        subprocess.Popen(
            ["osascript", "-e", script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception as e:
        print(f"[Notify] ERROR sending macOS notification: {e}")

# ===================== USER SETTINGS ===================== #
PORT = "COM3" if IS_WINDOWS else "/dev/cu.usbmodem14101"
# (later: auto-detect windows/mac/linux and auto-detect port)
BAUD = 115200
FS_HZ = 100.0  # expected IMU sample rate

# Units (set these to match your firmware output)
GYRO_IS_DPS = True   # True if gyro is in deg/s; will be converted to rad/s
ACCEL_IS_G = False   # True if accel is in g; will be converted to m/s^2

# Cursor control
SENS_X = 40.0  # pixels per rad/s using Gyro X (tilt around Y axis)
SENS_Y = 35.0  # pixels per rad/s using Gyro Y (tilt around X axis)
DEADZONE = 0.01       # rad/s; ignore tiny motions
EMA_ALPHA = 0.25      # [0..1] higher -> more responsive, less smoothing
MAX_STEP = 20         # cap per-update pixel move (safety)

# Scroll
SCROLL_STEP = 2

# ===== Edge-scroll (hold cursor at screen edge + hold 'j') =====
EDGE_MARGIN = 120        # pixels from each screen edge to count as "edge"
EDGE_DWELL_S = 0.25      # seconds to keep the cursor at the edge before scrolling starts
EDGE_SCROLL_HZ = 3.0     # repeat rate while edge-scrolling (events per second)

# ===== Hover-zone scroll (hold 'j' + keep cursor in top/bottom/left/right bands) =====
# Start zones below app chrome (tabs/menu/search bars)
TOP_ZONE_OFFSET_PX = 160   # <-- adjust until this sits just below tabs/search bar
BOTTOM_ZONE_OFFSET_PX = 30
LEFT_ZONE_OFFSET_PX = 0
RIGHT_ZONE_OFFSET_PX = 0

# Zone thickness (how deep the bands extend into the screen)
TOP_ZONE_PX = 140
BOTTOM_ZONE_PX = 260
LEFT_ZONE_PX = 120
RIGHT_ZONE_PX = 120

# Fractional thickness (fallback if you prefer responsive bands)
TOP_ZONE_FRAC = 0.45
BOTTOM_ZONE_FRAC = 0.45
LEFT_ZONE_FRAC = 0.35
RIGHT_ZONE_FRAC = 0.35

# Dwell + repeat (same feel as edge)
ZONE_DWELL_S = 0.2
ZONE_SCROLL_HZ = 4.0

# ===== Zoom gestures =====
ZOOM_STEPS = 1  # how much to scroll while holding Ctrl/Cmd to zoom.
DOUBLE_CLICK_MAX_GAP = 0.35  # seconds between taps to count as a double-click
TAP_MAX_DURATION = 0.25      # max duration (s) for a tap that can count toward a double-click
LONG_PRESS_MIN = 2.0         # secs (inclusive) for a zoom-out
LONG_PRESS_MAX = 9.0         # secs (inclusive) for a zoom-out
LASER_HOLD_MIN = 1.5         # secs (inclusive) for laser toggle in Presentation mode
SCROLL_ARM_DELAY = 0.35      # delay after press before enabling scroll detector
ZOOM_HOLD_REPEAT_HZ = 8.0    # how many zoom steps per second while holding
ZOOM_METHOD = 'hotkey'       # 'hotkey' or 'wheel'

# Hotkeys
QUIT_KEY = 'q'
CALIB_KEY = 'c'   # recalibrate gravity/bias for scroll detector
RESET_KEY = 'r'   # re-center cursor and zero filters

# ===== Cursor axis mapping (for full orientation calibration) =====
REF_AXIS_S = np.array([1.0, 0.0, 0.0])  # sensor axis that should map to screen +X (right)
DIR_X = +1.0  # flip to -1.0 if ring right-tilt moves cursor left
DIR_Y = +1.0  # flip to -1.0 if ring forward-tilt moves cursor up

# ===== Interactive calibration (press 'c') =====
CALIB_G_SAMPLES = 200        # ~2.0 s at 100 Hz for gravity average
CALIB_GYRO_QUIET = 0.25      # rad/s; only collect gravity samples when quiet
CALIB_ACC_VAR_MAX = 0.10     # (m/s^2)^2 per-axis variance limit while sampling gravity
CALIB_TILT_THRESH = 1.5      # m/s^2 horizontal accel needed to count as a "tilt"
CALIB_TILT_HOLD_FRAMES = 8   # consecutive frames over threshold to accept the tilt
CALIB_READ_DELAY = 5.0       # seconds to give user to read each prompt before sampling

# ===================== PACKET PARSER ===================== #
#
# Accept lines like: Accel X: -0.1 Y: 0.2 Z: -9.7 Gyro X: 2.3 Y: -1.2 Z: 0.0 Btn:1
LINE_RE = re.compile(
    r"Accel\s*X:\s*([-0-9.]+)\s*Y:\s*([-0-9.]+)\s*Z:\s*([-0-9.]+).*?"
    r"Gyro\s*X:\s*([-0-9.]+)\s*Y:\s*([-0-9.]+)\s*Z:\s*([-0-9.]+)"
    r"(?:.*?(?:Btn|Button)\s*[:=]\s*([01]))?",
    re.IGNORECASE
)
# Second button (right-click)
BTN2_RE = re.compile(r"(?:Btn2|Button2)\s*[:=]\s*([01])", re.IGNORECASE)

# === Switch input source: BLE vs Serial ===
USE_BLE = True

# On Windows, Bleak usually wants a MAC-like address or just connect by name.
BLE_ADDRESS = None if IS_WINDOWS else "5BEBAB28-B783-D576-5C23-585ED84E7371"
BLE_NAME_CONTAINS = "EngineeRing"   # or whatever your device advertises as

# from BLE scan output (166A0139-275D-6C6A-1044-3FA66E077052 for non flex pcb, 1A29B4FF-EE42-A12C-9BA1-8FAF0DCDCEE7 for flex)

# === IMU scaling for raw int16 coming from the ring firmware ===
# Replace with your firmware's actual ranges if different.
ACCEL_LSB_PER_G = 16384.0  # ICM-20948 in ±2g mode (1 g ≈ 16384 LSB)
GYRO_LSB_PER_DPS = 65.5    # ICM-20948 typical for ±500 dps (131 for ±250, 32.8 for ±1000, 16.4 for ±2000)

QUIT_HOLD_S = 5.0

ALERT_TIMEOUT_S = 5  # auto-dismiss alerts after 5 seconds

def parse_line(s: str):
    s = s.strip()
    if not s:
        return None
    # 1) Try labeled format first (e.g., "Accel X: ... Gyro ... Btn:")
    m = LINE_RE.search(s)
    if m:
        ax, ay, az, gx, gy, gz = map(float, m.groups()[:6])
        # buttons: optional
        btn1 = m.group(7)
        btn1 = int(btn1) if btn1 is not None else None
        # optional Btn2 on a separate token/line
        m2 = BTN2_RE.search(s)
        btn2 = int(m2.group(1)) if m2 else None
        # unit conversions
        if ACCEL_IS_G:
            ax *= 9.80665; ay *= 9.80665; az *= 9.80665
        if GYRO_IS_DPS:
            gx *= np.pi/180.0; gy *= np.pi/180.0; gz *= np.pi/180.0
        return ax, ay, az, gx, gy, gz, btn1, btn2

    # 2) Fallback: raw numeric format "ax ay az gx gy gz"
    parts = s.replace("\t", " ").replace(",", " ").split()
    if len(parts) == 6:
        try:
            ax, ay, az, gx, gy, gz = map(float, parts)
        except ValueError:
            return None
        if ACCEL_IS_G:
            ax *= 9.80665; ay *= 9.80665; az *= 9.80665
        if GYRO_IS_DPS:
            gx *= np.pi/180.0; gy *= np.pi/180.0; gz *= np.pi/180.0
        return ax, ay, az, gx, gy, gz, None, None

    return None

def _to_mps2_from_raw(raw_i16):
    g = float(raw_i16) / ACCEL_LSB_PER_G
    return g * 9.80665

def _to_rads_from_raw(raw_i16):
    dps = float(raw_i16) / GYRO_LSB_PER_DPS
    return math.radians(dps)

# ===================== HELPERS ===================== #
def _norm(v):
    return float(np.linalg.norm(v))

def _unit(v):
    n = _norm(v)
    return v / n if n > 1e-12 else v*0.0

# ===== Presentation detection helpers (macOS) =====
def _get_chrome_active_url():
    """
    On macOS, ask Google Chrome directly for the URL of the active tab in the
    front window. We do NOT require Chrome to be the 'frontmost' app, so this
    still works when Slides is in full-screen on another Space.
    """
    if sys.platform != "darwin":
        return ""
    script = r'''
    tell application "Google Chrome"
        if (count of windows) = 0 then return ""
        set theWin to front window
        if (count of tabs of theWin) = 0 then return ""
        return URL of active tab of theWin
    end tell
    '''
    try:
        out = subprocess.check_output(["osascript", "-e", script])
        return out.decode("utf-8").strip()
    except Exception as e:
        # Optional: debug the AppleScript failure
        # print(f"[SlidesDebug] AppleScript error: {e}")
        return ""

# ===================== SCROLL GESTURE DETECTOR ===================== #
class GestureScrollDetector:
    """
    Detects 'SCROLL_UP'/'SCROLL_DOWN' while button is held.
    Orientation-robust:
    - estimates gravity from accel (low-pass)
    - projects gyro into plane perpendicular to gravity
    - uses accel change along gravity to decide up vs down
    """
    def __init__(self, fs_hz=100.0,
                 min_burst_ms=120, max_burst_ms=700,
                 gyro_mag_thresh=2.0,      # rad/s
                 gyro_energy_thresh=15.0,  # integrated |ω| across burst
                 accel_grav_delta_thresh=0.6,  # m/s^2
                 debounce_ms=350,
                 gravity_lp_tau=0.6,
                 calib_samples=120):
        self.fs = fs_hz
        self.dt = 1.0/fs_hz
        self.min_burst = int(min_burst_ms * fs_hz / 1000.0)
        self.max_burst = int(max_burst_ms * fs_hz / 1000.0)
        self.gyro_mag_thresh = gyro_mag_thresh
        self.gyro_energy_thresh = gyro_energy_thresh
        self.accel_grav_delta_thresh = accel_grav_delta_thresh
        self.debounce_s = debounce_ms/1000.0

        self.g_bias = np.zeros(3)         # gyro bias
        self.g_hat = np.array([0.0,0.0,1.0]) # gravity unit vector
        self.a_g_baseline = 9.81

        self.lp_alpha = self.dt / (gravity_lp_tau + self.dt)
        self.buffer = deque(maxlen=self.max_burst*2)

        self.in_burst = False
        self.burst_start_len = 0
        self.last_trigger_t = -1e9

        # calibration accumulators
        self._calibrating = True
        self._calib_total = calib_samples
        self._calib_left = calib_samples
        self._gyro_bias_accum = np.zeros(3)
        self._accel_avg_accum = np.zeros(3)

    def reset_calibration(self, samples=None):
        if samples is None:
            samples = self._calib_total
        self._calibrating = True
        self._calib_total = samples
        self._calib_left = samples
        self._gyro_bias_accum[:] = 0
        self._accel_avg_accum[:] = 0

    def _calib_step(self, a, g):
        self._gyro_bias_accum += g
        self._accel_avg_accum += a
        self._calib_left -= 1
        if self._calib_left <= 0:
            self.g_bias = self._gyro_bias_accum / float(self._calib_total)
            a_mean = self._accel_avg_accum / float(self._calib_total)
            self.g_hat = _unit(a_mean)
            self.a_g_baseline = float(np.dot(a_mean, self.g_hat))
            self._calibrating = False
            notify(f"[Calib] Done. Gyro bias={self.g_bias.round(4)}, g_hat={self.g_hat.round(3)}, |g| baseline={self.a_g_baseline:.3f} m/s^2")

    def update(self, ax, ay, az, gx, gy, gz, button_held, t_now):
        a = np.array([ax, ay, az], dtype=float)
        g_raw = np.array([gx, gy, gz], dtype=float)

        if self._calibrating:
            self._calib_step(a, g_raw)
            return None

        # update gravity estimate (only when not interacting)
        if not button_held:
            self.g_hat = _unit((1.0 - self.lp_alpha)*self.g_hat + self.lp_alpha*a)
            self.a_g_baseline = float(np.dot(a, self.g_hat))

        # bias-corrected gyro
        g = g_raw - self.g_bias
        # project gyro to plane ⟂ gravity
        g_par = np.dot(g, self.g_hat) * self.g_hat
        g_proj = g - g_par

        gyro_mag = _norm(g_proj)
        a_g = float(np.dot(a, self.g_hat))
        da_g = a_g - self.a_g_baseline
        self.buffer.append((g_proj, da_g))

        # require button and debounce
        if not button_held or (t_now - self.last_trigger_t) < self.debounce_s:
            self.in_burst = False
            self.burst_start_len = 0
            return None

        # burst logic
        if not self.in_burst:
            if gyro_mag > self.gyro_mag_thresh:
                self.in_burst = True
                self.burst_start_len = len(self.buffer)
                return None
        else:
            burst_len = len(self.buffer) - self.burst_start_len
            if burst_len >= self.max_burst or gyro_mag < 0.4*self.gyro_mag_thresh:
                burst = list(self.buffer)[self.burst_start_len:]
                self.in_burst = False
                return self._analyze_and_classify(burst, t_now)
        return None

    def _analyze_and_classify(self, burst, t_now):
        n = len(burst)
        if n < self.min_burst:
            return None

        G = np.stack([s[0] for s in burst], axis=0)  # projected gyro (n,3)
        dAg = np.array([s[1] for s in burst])        # accel change along g (n,)

        # principal swing axis in motion plane
        U,S,Vt = np.linalg.svd(G, full_matrices=False)
        axis = Vt[0]
        signed_gyro = G @ axis
        ang_impulse = float(np.trapz(np.abs(signed_gyro), dx=1.0/self.fs))
        mean_abs_dAg = float(np.mean(np.abs(dAg)))
        mean_dAg = float(np.mean(dAg))

        # gates
        if ang_impulse < self.gyro_energy_thresh:
            return None
        if mean_abs_dAg < self.accel_grav_delta_thresh:
            return None

        label = "SCROLL_DOWN" if mean_dAg < 0.0 else "SCROLL_UP"
        self.last_trigger_t = t_now
        return label

# ===================== CURSOR FILTER ===================== #
class EMA:
    def __init__(self, alpha):
        self.alpha = float(alpha)
        self.y = 0.0
    def reset(self, v=0.0):
        self.y = float(v)
    def set_alpha(self, alpha):
        self.alpha = float(alpha)
    def update(self, x):
        self.y = self.alpha * x + (1.0 - self.alpha) * self.y
        return self.y

# ===================== MAIN APP ===================== #
class IMU2MouseApp:
    def __init__(self, port, baud, launch_osk=False, use_ble=False, ble_address=None):
        self.port = port
        self.baud = baud
        self.running = True

        # Attach HUD to this app
        try:
            self.hud = RingHUD(size=200, corner="bottom-right")
            self.hud.set_mode("POINTER")
        except Exception as e:
            print(f"[HUD] Error creating HUD: {e}")
            self.hud = None

        # Modes + mode-toggle settings
        # POINTER mode = default when both flags below are False
        self.typing_mode = False                # Typing mode flag
        self.presentation_mode = False          # Presentation mode flag
        self.J_MODE_HOLD_S = 5.0                # seconds to hold J to cycle modes
        self.j_long_mode_triggered = False      # tracks if this press already toggled

        # --- Rehabilitation background logger (always-on) ---
        self.rehab_session_active = False       # True while a background session is running
        self.rehab_start_time = None

        # Per-session metrics
        self.rehab_rom_values = []              # wrist/hand tilt angles (deg)
        self.rehab_ang_vel_values = []          # angular speed (deg/s)
        self.rehab_zero_crossings = 0           # for rough rep counting
        self.rehab_last_tilt = None             # previous tilt along X for zero-cross
        self.rehab_typed_chars = 0              # letters typed during rehab session
        self.rehab_active_frames = 0            # frames where movement is "active"

        # Global typing counter (used only in typing mode)
        self.total_typed_chars = 0

        self.button_override = False   # from keyboard spacebar
        self.use_keyboard_btn = True   # set False if device sends Btn: field

        self.detector = GestureScrollDetector(fs_hz=FS_HZ)
        self.ema_vx = EMA(EMA_ALPHA)
        self.ema_vy = EMA(EMA_ALPHA)
        self.ser = None

        # --- BLE input (must live in __init__) ---
        self.use_ble = use_ble
        self.ble_address = ble_address
        self.ring = None

        # --- Gesture state (for SPACE tap/hold logic) ---
        self.prev_btn = False
        self.press_t = None
        self.last_tap_end = -1e9
        self.pending_single_click = False
        self.single_click_deadline = -1e9
        self.longpress_active = False
        self.next_zoom_tick = 0.0

        # SPACE (left button) annotation state in Presentation mode
        self.space_annotate_triggered = False

        # Scroll testing (hold 'j' to enable scroll detector)
        self.scroll_override = False  # 'j' acts as right-click button
        self.j_button_held = False    # live state of j being held
        self.j_prev_btn = False       # previous loop state
        self.j_press_t = None         # when j was pressed (for tap timing)
        self.J_TAP_MAX_DURATION = 0.25  # seconds max to count as a right-click tap

        # Edge-scroll state
        self.edge_scroll_active = False
        self.edge_dir = None  # 'UP'|'DOWN'|'LEFT'|'RIGHT'|None
        self.next_edge_tick = 0.0
        self.edge_enter_time = None  # when we first hit an edge (for dwell timing)

        # Zone-scroll state
        self.zone_scroll_active = False
        self.zone_dir = None  # 'UP'|'DOWN'|'LEFT'|'RIGHT'|None
        self.next_zone_tick = 0.0
        self.zone_enter_time = None

        # Interactive calibration wizard
        self.ic_state = 'idle'  # 'idle' | 'gravity' | 'ask_x_pos' | 'ask_x_neg'
        self.ic_g_sum = np.zeros(3)
        self.ic_g_keep = []   # accepted accel samples for variance check
        self.ic_g_n = 0
        self.ic_z = np.array([0.0, 0.0, 1.0])  # gravity (sensor frame) after step 1
        self.ic_x_dir = None  # +X direction (sensor frame) from the "tilt right" step
        self.ic_tilt_frames = 0  # consecutive over-threshold frames
        self.ic_ready_at = -1e9  # time until which tilt is ignored (reading grace period)
        self.R_s2w = np.eye(3)   # final rotation sensor->world

        # --- Manual BLE connect (both buttons hold) ---
        self.both_press_t = None
        self.prev_both_held = False
        self.both_long_triggered = False

        self.J_DOUBLE_GAP = DOUBLE_CLICK_MAX_GAP   # reuse same gap as SPACE, or set your own
        self.j_last_tap_end = -1e9
        self.j_pending_rclick = False
        self.j_single_deadline = -1e9
        self.j_spotlight_triggered = False

        # Typing-mode drift stabilization
        self.drift_still_time = 0.0
        self.drift_last_stable_pos = None
        self.DRIFT_MOTION_THRESH = 0.15   # rad/s; below this = "still"
        self.DRIFT_STILL_TIME_S = 3.0     # seconds of stillness before nudging
        self.DRIFT_NUDGE_ALPHA = 0.01     # fraction of distance to stable point per frame

        # Typing submodes: False = click-to-type, True = dwell-to-type
        self.dwell_submode = False
        self.DWELL_TRIGGER_S = 0.5       # seconds to dwell before auto-click
        self.DWELL_MOVE_THRESH = 8.0     # pixels cursor must move to count as "leaving" key
        self.dwell_anchor_pos = None
        self.dwell_start_t = None
        self.dwell_fired = False

        # Drag / text-highlight state for SPACE hold
        self.drag_active = False
        self.tap_count = 0  # for SPACE triple-tap

        # SPACE tap clustering (for single vs double in Presentation mode)
        self.space_pending_click = False
        self.space_single_deadline = -1e9

        # Track whether WE think a slideshow is currently running
        self.slideshow_running = False

        # Track whether we think annotation/pen mode is active
        self.annotation_active = False

        # --- Temporary mode switch for blocking popups (e.g., PPT annotation dialog) ---
        self._modal_prev_mode = None    # "pointer" | "typing" | "presentation" | None
        self._modal_watch_until = 0.0   # time until which we keep checking for the dialog
        self._modal_active = False      # are we currently in a temp "popup" mode?

    def _try_ble_connect(self):
        """Attempt to connect to the ring over BLE. If already on BLE, do nothing.
           If currently on Serial, close it and switch to BLE on success.
        """
        if self.use_ble and self.ring:
            notify("EngineeRing is already connected.", blocking=False)
            return

        notify("Trying to connect EngineeRing…", blocking=False)
        try:
            # Close serial if it's open
            if self.ser and self.ser.is_open:
                try:
                    self.ser.close()
                except Exception:
                    pass

            # (Re)create BLE input and connect
            self.ring = RingBLEInput(device_name_contains=BLE_NAME_CONTAINS, address=self.ble_address)
            self.ring.start(timeout=50.0)
            self.use_ble = True
            notify("EngineeRing reconnected.", blocking=False)
        except Exception as e:
            self.use_ble = False
            print(f"[BLE] Manual connect failed: {e}")
            notify("Could not reconnect EngineeRing. Keeping current input.", blocking=False)

    def _start_interactive_calibration(self):
        """Start the full 3-step calibration flow (gravity + +X + -X)."""
        # Debug: console only
        print("[Calib] _start_interactive_calibration() called.")

        # Step 1/3 setup: gravity averaging
        self.ic_state = 'gravity'
        self.ic_g_sum[:] = 0.0
        self.ic_g_keep.clear()
        self.ic_g_n = 0
        self.ic_x_dir = None
        self.ic_tilt_frames = 0

        # Reset scroll detector bias/grav concurrently
        self.detector.reset_calibration(CALIB_G_SAMPLES)

        # Re-center cursor + zero filters
        try:
            w, h = pyautogui.size()
            pyautogui.moveTo(w / 2, h / 2, duration=0.15)
        except Exception as e:
            notify(f"[Calib] moveTo error: {e}")

        self.ema_vx.reset(0.0)
        self.ema_vy.reset(0.0)

        # Blocking: user must read this
        notify("Calibration 1/3: hold the ring in your neutral pose and keep still.", blocking=True)
        print(f"[Calib] (collecting {CALIB_G_SAMPLES} still samples)")

    # ---------- keyboard handlers ----------
    def on_key_press(self, key):
        try:
            if hasattr(key, 'char') and key.char is not None:
                ch = key.char

                # Quit key
                if ch == QUIT_KEY:
                    self.running = False
                    return False

                # Count typed characters when in typing mode
                if self.typing_mode:
                    # Count only printable, non-whitespace chars as "letters"
                    if ch.isprintable() and not ch.isspace():
                        self.total_typed_chars += 1
                        if self.rehab_session_active:
                            self.rehab_typed_chars += 1

        except Exception:
            pass

    def _close_active_window(self):
        """Close/exit the currently focused window (Cmd+W on macOS, Alt+F4 on others)."""
        try:
            if sys.platform == "darwin":
                pyautogui.hotkey('command', 'w')
            elif sys.platform.startswith("win"):
                pyautogui.hotkey('alt', 'f4')
            else:
                # Linux / other: Alt+F4 is the common window close accelerator
                pyautogui.hotkey('alt', 'f4')

        except Exception as e:
            print(f"[CloseWindow] ERROR: {e}")

    def _detect_presentation_app(self):
        """
        Try to guess whether the *frontmost* app is Google Slides or PowerPoint.
        Returns: 'slides', 'ppt', or None.

        On macOS:
          - If Microsoft PowerPoint is frontmost → 'ppt'
          - Else if Google Chrome is frontmost AND active tab is a Slides deck → 'slides'
        On other platforms:
          - Use window title via pygetwindow.
        """
        # ----- macOS: use System Events to know the real frontmost app -----
        if sys.platform == "darwin":
            front_app = ""
            try:
                script = '''
                tell application "System Events"
                    set frontApp to name of first application process whose frontmost is true
                end tell
                return frontApp
                '''
                front_app = subprocess.check_output(
                    ["osascript", "-e", script]
                ).decode("utf-8").strip()
            except Exception:
                front_app = ""

            # 1) If PowerPoint is actually the front app, treat it as 'ppt'
            if front_app == "Microsoft PowerPoint":
                return "ppt"

            # 2) If Chrome is frontmost, then check if the active tab is a Slides deck
            if front_app == "Google Chrome":
                url = _get_chrome_active_url()
                if url:
                    try:
                        parsed = urlparse(url)
                        if ("docs.google.com" in parsed.netloc
                            and "/presentation/" in parsed.path):
                            return "slides"
                    except Exception:
                        pass

            # Anything else → no known presentation app
            return None

        # ----- Non-macOS: fall back to active window title -----
        if gw is None:
            return None
        try:
            win = gw.getActiveWindow()
            if not win:
                return None

            raw_title = getattr(win, "title", "")
            if callable(raw_title):
                raw_title = raw_title()
            title = (raw_title or "").lower()

            # Prefer PowerPoint if we see it
            if "powerpoint" in title or "slide show" in title:
                return "ppt"

            # Rough Slides detection on other platforms
            if "google slides" in title or "docs.google.com/presentation" in title:
                return "slides"

            return None
        except Exception:
            return None

    def _get_front_window_title(self) -> str:
        """Return the title of the frontmost window, or '' on error."""
        # macOS: use System Events
        if sys.platform == "darwin":
            script = r'''
            tell application "System Events"
                set frontApp to first application process whose frontmost is true
                tell frontApp
                    if (count of windows) is 0 then return ""
                    return name of front window
                end tell
            end tell
            '''
            try:
                out = subprocess.check_output(["osascript", "-e", script])
                return out.decode("utf-8").strip()
            except Exception:
                return ""
        # Other platforms: fall back to pygetwindow
        if gw is None:
            return ""
        try:
            win = gw.getActiveWindow()
            if not win:
                return ""
            title = getattr(win, "title", "")
            if callable(title):
                title = title()
            return title or ""
        except Exception:
            return ""
        
    def _ppt_annotation_dialog_visible(self) -> bool:
        """
        Heuristic: detect the PowerPoint 'keep/save ink annotations' dialog.
        We just look at the front window title for key words.
        """
        title = self._get_front_window_title().lower()
        if not title:
            return False

        # Common patterns: "Do you want to keep ink annotations?" etc.
        has_ink = ("annotation" in title) or ("ink" in title)
        has_decision = ("keep" in title) or ("save" in title) or ("discard" in title)

        return has_ink and has_decision

    def _set_mode(self, mode_name: str):
        """
        mode_name: 'pointer', 'typing', or 'presentation'
        """
        # reset flags first
        self.typing_mode = False
        self.presentation_mode = False

        self.slideshow_running = False   # whenever we switch modes, assume slideshow is off
        self.annotation_active = False   # leave annotation mode when changing modes

        if mode_name == "typing":
            self.typing_mode = True
            mode_label = "TYPING"
        elif mode_name == "presentation":
            self.presentation_mode = True
            mode_label = "PRESENTATION"
        else:
            # default back to pointer
            mode_label = "POINTER"

        # Update HUD label only (no HUD banner)
        if getattr(self, "hud", None) is not None:
            try:
                self.hud.set_mode(mode_label)
                # self.hud.show_banner(f"{mode_label} mode", duration_ms=4000)
            except Exception as e:
                print(f"[HUD] set_mode error: {e}")

        # Single short non-blocking banner
        notify(f"Mode: {mode_label}", blocking=False)

    # ---------- Rehabilitation helpers ----------

    def _start_rehab_session(self):
        """Initialize per-session rehab metrics."""
        self.rehab_session_active = True
        self.rehab_start_time = time.time()
        self.rehab_rom_values = []
        self.rehab_ang_vel_values = []
        self.rehab_zero_crossings = 0
        self.rehab_last_tilt = None
        self.rehab_typed_chars = 0
        notify("[Rehab] Background rehab logging started for this ring session.", blocking=False)

    def _rehab_update_metrics(self, a_world, gx, gy, gz, t_now):
        """
        Update rehab metrics for the current IMU sample.

        a_world: accel in world frame (x,y,z) from a_cal
        gx,gy,gz: angular velocity (rad/s) in sensor frame (we use magnitude)
        """
        axw, ayw, azw = float(a_world[0]), float(a_world[1]), float(a_world[2])

        # --- Range of Motion (ROM) estimate (deg) ---
        # Approximate tilt angle from horizontal vs vertical accel.
        horiz = math.sqrt(axw*axw + ayw*ayw)
        # small epsilon to avoid division by zero
        tilt_rad = math.atan2(horiz, abs(azw) + 1e-6)
        tilt_deg = math.degrees(tilt_rad)
        self.rehab_rom_values.append(tilt_deg)

        # --- Angular velocity magnitude (deg/s) ---
        ang_speed_rad = math.sqrt(gx*gx + gy*gy + gz*gz)
        ang_speed_deg = math.degrees(ang_speed_rad)
        self.rehab_ang_vel_values.append(ang_speed_deg)

        # --- Active usage time (frames with "real" movement) ---
        # Simple threshold: above ~10–15 deg/s counts as active motion
        ACTIVE_SPEED_THRESH_DEG_S = 12.0
        if ang_speed_deg > ACTIVE_SPEED_THRESH_DEG_S:
            self.rehab_active_frames += 1

        # --- Rough repetition counting via zero-crossings on X tilt ---
        TILT_THRESH = 1.5  # m/s^2 approx; ignore tiny noise
        current_tilt = axw

        if self.rehab_last_tilt is not None:
            # Only count zero-crossings when magnitude is above threshold on both sides
            if (abs(current_tilt) > TILT_THRESH) and (abs(self.rehab_last_tilt) > TILT_THRESH):
                if (current_tilt > 0 and self.rehab_last_tilt < 0) or (current_tilt < 0 and self.rehab_last_tilt > 0):
                    self.rehab_zero_crossings += 1

        self.rehab_last_tilt = current_tilt

    def _end_rehab_session(self):
        """Finalize metrics, write JSON summary + optional graph."""
        if not self.rehab_session_active or self.rehab_start_time is None:
            return

        end_t = time.time()
        duration_s = max(0.001, end_t - self.rehab_start_time)

        # ---------- Build timestamps for filenames + JSON ----------
        start_dt = datetime.datetime.fromtimestamp(self.rehab_start_time)
        end_dt   = datetime.datetime.fromtimestamp(end_t)

        # For filenames: rehab_session_YYYY-MM-DD_HH-MM-SS-HH-MM-SS.ext
        date_str  = start_dt.strftime("%Y-%m-%d")   # e.g., 2025-12-09
        start_str = start_dt.strftime("%H-%M-%S")   # e.g., 15-30-12
        end_str   = end_dt.strftime("%H-%M-%S")     # e.g., 16-04-55
        session_label = f"{date_str}_{start_str}-{end_str}"

        # For JSON metadata
        session_start_iso = start_dt.strftime("%Y-%m-%dT%H:%M:%S")
        session_end_iso   = end_dt.strftime("%Y-%m-%dT%H:%M:%S")
        iso_year, iso_week, _ = start_dt.isocalendar()

        rom_vals = self.rehab_rom_values[:] or [0.0]
        ang_vals = self.rehab_ang_vel_values[:] or [0.0]

        # ---------- Basic ROM & speed ----------
        avg_rom = float(sum(rom_vals) / len(rom_vals))
        max_rom = float(max(rom_vals))
        avg_ang = float(sum(ang_vals) / len(ang_vals))
        max_ang = float(max(ang_vals))

        # Rough reps = half the zero-crossings (pos→neg or neg→pos)
        reps = self.rehab_zero_crossings // 2

        # Letters per minute during rehab session (only while in typing mode)
        letters = int(self.rehab_typed_chars)
        letters_per_min = (letters / duration_s) * 60.0

        # ---------- 1) Smoothness / jerkiness index ----------
        if len(ang_vals) >= 2:
            diffs = [abs(ang_vals[i+1] - ang_vals[i]) for i in range(len(ang_vals) - 1)]
            jerk_index = float(sum(diffs) / len(diffs))
            smoothness_index = 1.0 / (1.0 + jerk_index)  # smaller jerk → closer to 1
        else:
            jerk_index = 0.0
            smoothness_index = 1.0

        # ---------- 2) Tremor index (high-frequency residual of speed) ----------
        # Simple moving average smooth, then take std of residual
        if len(ang_vals) >= 3:
            window = 5  # ~50 ms at 100 Hz
            smoothed = []
            n = len(ang_vals)
            for i in range(n):
                j0 = max(0, i - window)
                j1 = min(n, i + window + 1)
                segment = ang_vals[j0:j1]
                smoothed.append(sum(segment) / len(segment))
            residuals = [ang_vals[i] - smoothed[i] for i in range(n)]
            # std of residuals
            mean_res = sum(residuals) / len(residuals)
            tremor_index = float(
                math.sqrt(sum((r - mean_res) ** 2 for r in residuals) / max(1, len(residuals)))
            )
        else:
            tremor_index = 0.0

        # ---------- 3) Active usage time ----------
        active_time_s = float(self.rehab_active_frames) / float(FS_HZ)
        active_fraction = active_time_s / duration_s

        # ---------- 4) Speed drop over session ----------
        if len(ang_vals) >= 6:
            n = len(ang_vals)
            third = n // 3
            first_mean_speed = sum(ang_vals[:third]) / max(1, third)
            last_mean_speed = sum(ang_vals[-third:]) / max(1, third)
            if first_mean_speed > 1e-6:
                speed_drop_percent = 100.0 * (first_mean_speed - last_mean_speed) / first_mean_speed
            else:
                speed_drop_percent = 0.0
        else:
            speed_drop_percent = 0.0

        # ---------- 5) Smoothness change over session ----------
        def _segment_jerk(vals):
            if len(vals) < 2:
                return 0.0
            d = [abs(vals[i+1] - vals[i]) for i in range(len(vals) - 1)]
            return float(sum(d) / len(d))

        if len(ang_vals) >= 6:
            n = len(ang_vals)
            third = n // 3
            jerk_first = _segment_jerk(ang_vals[:third])
            jerk_last = _segment_jerk(ang_vals[-third:])
            if jerk_first > 1e-6:
                # Positive value = got jerkier over time; negative = smoother
                smoothness_change_percent = 100.0 * (jerk_last - jerk_first) / jerk_first
            else:
                smoothness_change_percent = 0.0
        else:
            smoothness_change_percent = 0.0

        # ---------- 6) ROM variability ----------
        if len(rom_vals) >= 2:
            rom_mean = avg_rom
            rom_var = sum((r - rom_mean) ** 2 for r in rom_vals) / max(1, len(rom_vals))
            rom_std = float(math.sqrt(rom_var))
        else:
            rom_std = 0.0

        # ---------- Simple ROM fatigue ----------
        if len(rom_vals) >= 6:
            n = len(rom_vals)
            third = n // 3
            first_mean = sum(rom_vals[:third]) / max(1, third)
            last_mean = sum(rom_vals[-third:]) / max(1, third)
            if first_mean > 1e-6:
                rom_drop_percent = 100.0 * (first_mean - last_mean) / first_mean
            else:
                rom_drop_percent = 0.0
        else:
            rom_drop_percent = 0.0

        # ---------- Build summary dict ----------
        summary = {
            "session_start_iso": session_start_iso,
            "session_end_iso": session_end_iso,
            "duration_s": duration_s,
            "iso_year": iso_year,
            "iso_week": iso_week,

            "motion_metrics": {
                "avg_rom_deg": avg_rom,
                "max_rom_deg": max_rom,
                "avg_ang_vel_deg_s": avg_ang,
                "max_ang_vel_deg_s": max_ang,
                "estimated_reps": int(reps),

                # 1) smoothness / jerkiness
                "smoothness_index": smoothness_index, # Macro-level control (big picture flow)
                "jerk_index": jerk_index, # Micro-level abruptness (precision transitions)

                # 2) tremor
                "tremor_index": tremor_index, # High-frequency noise/shaking (neuromuscular stability)
                # A rehab specialist could use these three together to distinguish between: lack of control vs muscle fatigue, 
                # intentional movement vs uncontrolled tremor, or improving consistency over time vs erratic motion

                # 3) active usage
                "active_usage_s": active_time_s,
                "active_usage_fraction": active_fraction,

                # 4) ROM variability (consistency)
                "rom_variability_std_deg": rom_std,
            },

            "functional_metrics": {
                "typed_letters": letters,
                "typed_letters_per_min": letters_per_min,
            },

            "fatigue_metrics": {
                # fatigue in movement range
                "rom_drop_percent": rom_drop_percent,

                # fatigue in speed
                "speed_drop_percent": speed_drop_percent,

                # fatigue in smoothness
                "smoothness_change_percent": smoothness_change_percent,
            }
        }

        # Save JSON file into: Desktop / school folder / Senior Design / Rehab Metrics
        logs_dir = "/Users/reemawad/Desktop/school folders/Senior Design/Rehab Metrics"
        os.makedirs(logs_dir, exist_ok=True)

        fname = f"rehab_session_{session_label}.json"
        fpath = os.path.join(logs_dir, fname)
        try:
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2)
        except Exception as e:
            print(f"[Rehab] Error writing summary file: {e}")
            fpath = None

        # Optional: simple ROM-over-time graph
        graph_path = None
        if plt is not None:
            try:
                t_axis = [i / float(FS_HZ) for i in range(len(rom_vals))]
                plt.figure()
                plt.plot(t_axis, rom_vals)
                plt.xlabel("Time (s)")
                plt.ylabel("Tilt angle (deg)")
                plt.title("Rehab Session ROM vs Time")
                plt.tight_layout()
                graph_path = os.path.join(logs_dir, f"rehab_rom_{session_label}.png")
                plt.savefig(graph_path)
                plt.close()
            except Exception as e:
                print(f"[Rehab] Error generating graph: {e}")
                graph_path = None

        # Reset session state
        self.rehab_session_active = False
        self.rehab_start_time = None
        self.rehab_rom_values = []
        self.rehab_ang_vel_values = []
        self.rehab_zero_crossings = 0
        self.rehab_last_tilt = None
        self.rehab_typed_chars = 0
        self.rehab_active_frames = 0

        # Short, high-level summary for the user
        msg_parts = [
            "[Rehab] Session saved.",
            f"Duration ≈ {duration_s/60.0:.1f} min",
            f"Reps ≈ {int(reps)}",
            f"Max ROM = {max_rom:.1f}°"
        ]

        if fpath:
            msg_parts.append(f"Summary file: {os.path.basename(fpath)}")
        if graph_path:
            msg_parts.append(f"Graph: {os.path.basename(graph_path)}")

        msg_parts.append(f"Folder: {logs_dir}")
        notify(" | ".join(msg_parts), blocking=False)

    def _start_slides_slideshow(self):
        """
        Try to start Google Slides slideshow for the active Slides tab.
        On macOS we use Cmd+Shift+Return.
        """
        try:
            if sys.platform == "darwin":
                pyautogui.hotkey('command', 'shift', 'enter')
            else:
                pyautogui.hotkey('ctrl', 'f5')
            # Optional: small non-blocking banner
            notify("Started Google Slides slideshow.", blocking=False)
        except Exception as e:
            print(f"[Presentation] Error starting Google Slides slideshow: {e}")

    def _start_powerpoint_slideshow(self):
        """
        Start PowerPoint slideshow of the active presentation.
        On macOS we prefer AppleScript and fall back to F5.
        """
        if sys.platform == "darwin":
            script = r'''
            tell application "Microsoft PowerPoint"
                if (count of presentations) > 0 then
                    start slide show active presentation
                end if
            end tell
            '''
            try:
                subprocess.check_call(["osascript", "-e", script])
                notify("[Presentation] Requested PowerPoint slideshow start via AppleScript.")
                return
            except Exception as e:
                notify(f"[Presentation] AppleScript start failed, trying F5: {e}")
        # fallback for any platform
        try:
            pyautogui.press('f5')
            notify("[Presentation] Requested PowerPoint slideshow start via F5.")
        except Exception as e:
            notify(f"[Presentation] Error starting PowerPoint slideshow: {e}")

    def _toggle_laser_pointer(self):
        """
        Toggle laser pointer vs normal mouse cursor in slideshow
        for Google Slides or PowerPoint.
        """
        app = self._detect_presentation_app()
        try:
            if app == "slides":
                # In Google Slides slideshow, 'L' toggles the laser pointer
                pyautogui.press("l")
                notify("[Presentation] Toggled Google Slides laser pointer (key 'L').")
            elif app == "ppt":
                # In PowerPoint slideshow, Ctrl+L (or Command+L on macOS) toggles laser
                if sys.platform == "darwin":
                    pyautogui.hotkey("command", "l")
                else:
                    pyautogui.hotkey("ctrl", "l")
                notify("[Presentation] Toggled PowerPoint laser pointer (Ctrl/Command+L).")
            else:
                notify("[Presentation] Laser toggle requested, but no Slides/PowerPoint detected.")
        except Exception as e:
            print(f"[Presentation] Error toggling laser pointer: {e}")

    def _toggle_annotation(self):
        """
        Toggle annotation/pen mode in slideshow
        for Google Slides or PowerPoint.
        """
        app = self._detect_presentation_app()
        try:
            if app == "slides":
                if sys.platform == "darwin":
                    pyautogui.hotkey("shift", "l")
                else:
                    pyautogui.press("p")
            elif app == "ppt":
                if sys.platform == "darwin":
                    pyautogui.hotkey("command", "p")
                else:
                    pyautogui.hotkey("ctrl", "p")
            else:
                # Non-blocking because it’s not critical, just user feedback
                notify("No slideshow window found for annotation.", blocking=False)
                return
        except Exception as e:
            print(f"[Presentation] Error toggling annotation: {e}")
            return

        # Flip our internal flag so we know whether annotation is on
        self.annotation_active = not self.annotation_active
        state_msg = "Annotation ON" if self.annotation_active else "Annotation OFF"
        notify(state_msg, blocking=False)

    def _left_click_action(self):
        """
        What a confirmed SPACE single-tap does.
        """
        if self.presentation_mode:
            # Previous slide in Slides/PowerPoint
            pyautogui.press("right")
        else:
            pyautogui.click()

    def _right_click_action(self):
        """
        What a confirmed J single-tap does.
        """
        if self.presentation_mode:
            # Next slide in Slides/PowerPoint
            pyautogui.press("left")
        else:
            pyautogui.click(button="right")

    def on_key_release(self, key):
        try:
            # No keyboard key releases affect ring behavior anymore
            pass
        except Exception:
            pass

    def _mod_key(self):
        return 'command' if sys.platform == 'darwin' else 'ctrl'

    def _zoom_in_step(self):
        """Triple-tap SPACE → zoom in via Cmd/Ctrl + '='."""
        if self.typing_mode or self.presentation_mode:
            return
        pyautogui.hotkey(self._mod_key(), '=')

    def _zoom_out_step(self):
        """Hold SPACE → continuous zoom out via Cmd/Ctrl + '-'."""
        if self.typing_mode or self.presentation_mode:
            return
        pyautogui.hotkey(self._mod_key(), '-')

    def _edge_scroll_direction(self, x, y, sw, sh):
        """ Return which edge we're at, or None if not at an edge.
            Priority: corners pick the *closer* edge by proximity.
        """
        dir_candidates = []
        if y <= EDGE_MARGIN:
            dir_candidates.append(('UP', y))
        if y >= sh - 1 - EDGE_MARGIN:
            dir_candidates.append(('DOWN', (sh - 1 - y)))
        if x <= EDGE_MARGIN:
            dir_candidates.append(('LEFT', x))
        if x >= sw - 1 - EDGE_MARGIN:
            dir_candidates.append(('RIGHT', (sw - 1 - x)))
        if not dir_candidates:
            return None
        dir_candidates.sort(key=lambda t: t[1])  # smaller distance = closer to edge
        return dir_candidates[0][0]

    def _do_edge_scroll(self, direction):
        """ Perform one scroll 'tick' for the given direction.
            Uses horizontal scroll if available; otherwise Shift+vertical as fallback.
        """
        if self.typing_mode or self.presentation_mode:
            return  # no scrolling in typing mode

        HSCROLL_STEP = 1  # smaller = slower horizontal
        try:
            if direction == 'UP':
                pyautogui.scroll(+SCROLL_STEP)
                return
            if direction == 'DOWN':
                pyautogui.scroll(-SCROLL_STEP)
                return
            if direction in ('LEFT', 'RIGHT'):
                if hasattr(pyautogui, 'hscroll'):
                    # LEFT band → scroll left (positive); RIGHT → scroll right (negative)
                    pyautogui.hscroll(+HSCROLL_STEP if direction == 'LEFT' else -HSCROLL_STEP)
                else:
                    # Fallback: Shift + vertical emulates horizontal
                    pyautogui.keyDown('shift')
                    try:
                        # Many apps treat Shift+wheel-up as "scroll right"
                        pyautogui.scroll(+SCROLL_STEP if direction == 'RIGHT' else -SCROLL_STEP)
                    finally:
                        pyautogui.keyUp('shift')
            # else: ignore unknown directions / None
        except Exception as e:
            print(f"[Scroll] ERROR: {e}")

    def _zone_scroll_direction(self, x, y, sw, sh):
        """ Return 'UP'/'DOWN'/'LEFT'/'RIGHT' if cursor is inside a hover-zone, else None.
            Uses dynamic (fractional) band sizes each frame.
        """
        # Dynamic band thickness (in pixels)
        top_px = max(1, int(TOP_ZONE_FRAC * sh))
        bottom_px = max(1, int(BOTTOM_ZONE_FRAC * sh))
        left_px = max(1, int(LEFT_ZONE_FRAC * sw))
        right_px = max(1, int(RIGHT_ZONE_FRAC * sw))

        candidates = []
        # Top zone: from TOP_ZONE_OFFSET_PX .. TOP_ZONE_OFFSET_PX + top_px
        if TOP_ZONE_OFFSET_PX <= y <= TOP_ZONE_OFFSET_PX + top_px:
            candidates.append(('UP', y - TOP_ZONE_OFFSET_PX))
        # Bottom zone: from (sh - BOTTOM_ZONE_OFFSET_PX - bottom_px) .. (sh - BOTTOM_ZONE_OFFSET_PX)
        if (sh - BOTTOM_ZONE_OFFSET_PX - bottom_px) <= y <= (sh - BOTTOM_ZONE_OFFSET_PX):
            candidates.append(('DOWN', (sh - BOTTOM_ZONE_OFFSET_PX) - y))
        # Left zone: from LEFT_ZONE_OFFSET_PX .. LEFT_ZONE_OFFSET_PX + left_px
        if LEFT_ZONE_OFFSET_PX <= x <= LEFT_ZONE_OFFSET_PX + left_px:
            candidates.append(('LEFT', x - LEFT_ZONE_OFFSET_PX))
        # Right zone: from (sw - RIGHT_ZONE_OFFSET_PX - right_px) .. (sw - RIGHT_ZONE_OFFSET_PX)
        if (sw - RIGHT_ZONE_OFFSET_PX - right_px) <= x <= (sw - RIGHT_ZONE_OFFSET_PX):
            candidates.append(('RIGHT', (sw - RIGHT_ZONE_OFFSET_PX) - x))

        if not candidates:
            return None
        candidates.sort(key=lambda t: t[1])  # “closer to inner edge” wins
        return candidates[0][0]

    def _build_R_from_accel(self, a_mean, ref_axis_s=REF_AXIS_S):
        """ Build rotation R_s2w (sensor → world) using:
            - a_mean: average accel (gravity) in sensor frame
            - ref_axis_s: sensor-space axis that should point toward world +X (screen right)
            World frame: +Z = down (gravity), X/Y in horizontal plane.
            v_world = R_s2w @ v_sensor
        """
        z = _unit(a_mean)  # gravity direction in sensor frame (down)
        # Project the chosen sensor axis onto the plane perpendicular to z
        r = np.array(ref_axis_s, dtype=float)
        r_par = np.dot(r, z) * z
        r_perp = r - r_par
        if _norm(r_perp) < 1e-6:
            # If ref axis is nearly collinear with gravity, fall back to another sensor axis
            alt = np.array([0.0, 1.0, 0.0])
            r_par = np.dot(alt, z) * z
            r_perp = alt - r_par
        x = _unit(r_perp)          # world +X (right)
        y = _unit(np.cross(z, x))  # world +Y (forward)
        R = np.vstack([x, y, z])   # rows are world basis in sensor frame
        return R

    def _interactive_calib_step(self, ax, ay, az, gx, gy, gz):
        """ Run one step of the interactive calibration wizard.
            Returns True if calibration is in progress (so main loop can pause actions),
            False if idle.
        """
        state = self.ic_state
        if state == 'idle':
            return False

        a = np.array([ax, ay, az], dtype=float)

        # ---------- Step 1: gravity averaging while still ----------
        if state == 'gravity':
            gyro_mag = float((gx*gx + gy*gy + gz*gz) ** 0.5)
            # Keep a short window to check accel variance
            if not hasattr(self, "_ic_acc_win"):
                self._ic_acc_win = deque(maxlen=40)  # ~0.4 s at 100 Hz
            self._ic_acc_win.append(a)

            acc_var_ok = False
            if len(self._ic_acc_win) == self._ic_acc_win.maxlen:
                A = np.array(self._ic_acc_win, dtype=float)
                var = A.var(axis=0)
                acc_var_ok = bool((var < CALIB_ACC_VAR_MAX).all())

            if (gyro_mag < CALIB_GYRO_QUIET) and acc_var_ok:
                self.ic_g_sum += a
                self.ic_g_keep.append(a)
                self.ic_g_n += 1
                if self.ic_g_n % 50 == 0:
                    print(f"[Calib] … {self.ic_g_n}/{CALIB_G_SAMPLES} good samples")

            if self.ic_g_n >= CALIB_G_SAMPLES:
                a_mean = self.ic_g_sum / float(self.ic_g_n)
                gmag = _norm(a_mean)
                if not (8.5 <= gmag <= 10.7):
                    notify(f"Calibration failed (|g|={gmag:.2f} m/s²). Keep still and press 'c' again.", blocking=True)

                    self.ic_state = 'idle'
                    return False
                self.ic_z = _unit(a_mean)  # gravity direction (sensor frame)
                self.ic_state = 'ask_x_pos'
                self.ic_tilt_frames = 0
                notify("Calibration 2/3: tilt ring to your RIGHT and hold.", blocking=True)
                self.ic_ready_at = time.time() + CALIB_READ_DELAY
                return True

        # Helper: horizontal component relative to gravity
        z = self.ic_z
        horiz = a - np.dot(a, z) * z
        horiz_norm = _norm(horiz)

        # ---------- Step 2: capture +X (right tilt) ----------
        if state == 'ask_x_pos':
            # grace period to read the prompt
            if time.time() < self.ic_ready_at:
                self.ic_tilt_frames = 0
                return True

            if horiz_norm > CALIB_TILT_THRESH:
                self.ic_tilt_frames += 1
            else:
                self.ic_tilt_frames = 0

            if self.ic_tilt_frames >= CALIB_TILT_HOLD_FRAMES:
                self.ic_x_dir = _unit(horiz)
                self.ic_state = 'ask_x_neg'
                self.ic_tilt_frames = 0
                notify("Calibration 3/3: tilt ring to your LEFT and hold.", blocking=True)
                self.ic_ready_at = time.time() + CALIB_READ_DELAY
                return True

        # ---------- Step 3: confirm -X (left tilt) and finish ----------
        if state == 'ask_x_neg':
            # grace period to read the prompt
            if time.time() < self.ic_ready_at:
                self.ic_tilt_frames = 0
                return True

            # We just need to see substantial tilt in the opposite direction
            opp_component = np.dot(horiz, self.ic_x_dir)  # positive if same side, negative if opposite
            if (horiz_norm > CALIB_TILT_THRESH) and (opp_component < -0.5 * horiz_norm):
                x = -self.ic_x_dir
                y = _unit(np.cross(z, x))  # right-handed: y = z × x
                R = np.vstack([x, y, z])   # rows are world basis in sensor frame
                self.R_s2w = R
                # Seed scroll detector gravity to match (optional but helpful)
                self.detector.g_hat = _unit(a)
                self.detector.a_g_baseline = float(np.dot(a, self.detector.g_hat))
                notify("Calibration complete. Orientation updated.", blocking=False)
                print(" R_s2w rows:\n"
                      f" X←sens: {self.R_s2w[0].round(3)}\n"
                      f" Y←sens: {self.R_s2w[1].round(3)}\n"
                      f" Z←sens: {self.R_s2w[2].round(3)}")
                self.ic_state = 'idle'
                return False

        return True

    # ---------- core loop ----------
    def run(self):
        SAFE_MARGIN = 5  # keep cursor away from screen edges
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0

        # start keyboard listener
        listener = keyboard.Listener(on_press=self.on_key_press, on_release=self.on_key_release)
        listener.start()

        if self.use_ble:
            try:
                print("[BLE] Connecting to ring…")
                self.ring = RingBLEInput(device_name_contains=BLE_NAME_CONTAINS, address=self.ble_address)
                self.ring.start(timeout=20.0)

                # Blocking startup toast (BLE success)
                notify("EngineeRing connected via BLE. Mouse is running.", blocking=True)
            except Exception as e:
                print(f"[BLE] ERROR: {e}")
                # Blocking failure toast and exit (no NO-IMU mode)
                notify("EngineeRing could not connect over BLE. Exiting.", blocking=True)
                self.running = False
                return

        # open serial (fallback / or when BLE is off)
        if not self.use_ble:
            try:
                self.ser = serial.Serial(self.port, self.baud, timeout=1)
                print(f"[Serial] Opened {self.port} @ {self.baud}")
                notify("EngineeRing connected over USB. Mouse is running.", blocking=True)
            except Exception as e:
                ...
        else:
            self.ser = None

        # Start one background rehab logging session for the whole ring usage
        self._start_rehab_session()

        while self.running:
            try:
                # Keep HUD responsive
                if getattr(self, "hud", None) is not None:
                    self.hud.pump()

                    # ----- ZONE-SCROLL LOGIC (runs even if no new serial yet) -----
                    t_now = time.time()

                    # ----- Temporary mode switch for PowerPoint 'keep your ink annotations' dialog -----
                    if self._modal_watch_until > 0.0 and t_now <= self._modal_watch_until:
                        if not self._modal_active:
                            # Waiting for the dialog to appear
                            if self._ppt_annotation_dialog_visible():
                                current = (
                                    "presentation" if self.presentation_mode
                                    else ("typing" if self.typing_mode else "pointer")
                                )
                                self._modal_prev_mode = self._modal_prev_mode or current

                                if current != "pointer":
                                    self._set_mode("pointer")

                                self._modal_active = True
                        else:
                            # Dialog is active — restore once it disappears
                            if not self._ppt_annotation_dialog_visible():
                                prev = self._modal_prev_mode
                                self._modal_prev_mode = None
                                self._modal_watch_until = 0.0
                                self._modal_active = False

                                if prev == "presentation":
                                    self._set_mode("presentation")
                                elif prev == "typing":
                                    self._set_mode("typing")
                                else:
                                    self._set_mode("pointer")
                    elif self._modal_active:
                        # Watch window expired but still marked active → restore just in case
                        prev = self._modal_prev_mode
                        self._modal_prev_mode = None
                        self._modal_watch_until = 0.0
                        self._modal_active = False

                        if prev == "presentation":
                            self._set_mode("presentation")
                        elif prev == "typing":
                            self._set_mode("typing")
                        else:
                            self._set_mode("pointer")

                    cx, cy = pyautogui.position()
                    sw, sh = pyautogui.size()

                if self.typing_mode or self.presentation_mode:
                    # Typing Mode → no zone scrolling at all
                    self.scroll_override = False
                    self.zone_scroll_active = False
                    self.zone_dir = None
                    self.zone_enter_time = None
                else:
                    # If last frame had left button down AND J is down now,
                    # treat it as a chord → no scroll override.
                    if self.prev_btn and self.j_button_held:
                        self.scroll_override = False
                        self.zone_scroll_active = False
                        self.zone_dir = None
                        self.zone_enter_time = None
                    else:
                        self.scroll_override = self.j_button_held  

                    if not self.scroll_override:
                        # 'j' not held (or we're in a chord) → reset zone state
                        self.zone_scroll_active = False
                        self.zone_dir = None
                        self.zone_enter_time = None
                    else:
                        at_zone_dir = self._zone_scroll_direction(cx, cy, sw, sh)
                        if at_zone_dir is None:
                            self.zone_scroll_active = False
                            self.zone_dir = None
                            self.zone_enter_time = None
                        else:
                            if self.zone_dir != at_zone_dir:
                                # new zone or changed zone → start dwell timer
                                self.zone_dir = at_zone_dir
                                self.zone_enter_time = t_now
                                self.zone_scroll_active = False
                                self.next_zone_tick = 0.0
                            else:
                                # same zone; after dwell, fire repeat scroll ticks
                                if (self.zone_enter_time is not None) and ((t_now - self.zone_enter_time) >= ZONE_DWELL_S):
                                    if not self.zone_scroll_active:
                                        self.zone_scroll_active = True
                                        self.next_zone_tick = t_now
                                    if t_now >= self.next_zone_tick:
                                        self._do_edge_scroll(self.zone_dir)
                                        self.next_zone_tick += 1.0 / max(1e-6, ZONE_SCROLL_HZ)

                # --- Read latest IMU/buttons from BLE or Serial ---
                parsed = None
                if self.use_ble and self.ring:
                    sample = self.ring.read()
                    if sample is None:
                        # nothing new this frame
                        pass
                    else:
                        # Convert raw int16 → physical units for your existing logic
                        ax = _to_mps2_from_raw(sample["ax"])
                        ay = _to_mps2_from_raw(sample["ay"])
                        az = _to_mps2_from_raw(sample["az"])
                        gx = _to_rads_from_raw(sample["gx"])
                        gy = _to_rads_from_raw(sample["gy"])
                        gz = _to_rads_from_raw(sample["gz"])

                        # Map buttons:
                        # Assume b1 bit0 = left (SPACE), b2 bit0 = J (right)
                        # Change bits as needed if your firmware uses different mapping.
                        b1 = int(sample["b1"])
                        b2 = int(sample["b2"])
                        # Active-low: idle=1, pressed=0 on the least-significant bit
                        btn1 = 1 if ((b1 & 0x01) == 0) else 0
                        btn2 = 1 if ((b2 & 0x01) == 0) else 0
                        parsed = (ax, ay, az, gx, gy, gz, btn1, btn2)

                if (parsed is None) and self.ser:
                    last = None
                    while self.ser.in_waiting:
                        last = self.ser.readline()
                    if last is None:
                        last = self.ser.readline()
                    if last:
                        line = last.decode('utf-8', errors='ignore').strip()
                        if line:
                            parsed = parse_line(line)

                if parsed is None:
                    # nothing new this frame
                    continue

                ax, ay, az, gx, gy, gz, btn1, btn2 = parsed

                # button: prefer device button; else spacebar fallback
                if btn1 is None and self.use_keyboard_btn:
                    button_held = self.button_override
                else:
                    button_held = bool(btn1)

                # 'j' button from device if available (btn2), otherwise keyboard 'j'
                if btn2 is not None:
                    self.j_button_held = bool(btn2)

                # --- HUD: update button indicators ---
                if getattr(self, "hud", None) is not None:
                    try:
                        self.hud.set_buttons(
                            left_down=button_held,
                            right_down=self.j_button_held
                        )
                    except Exception as e:
                        print(f"[HUD] set_buttons error: {e}")

                t_now = time.time()

                # ----- Both-buttons quit + calibration gesture (both buttons) -----
                both_held = bool(button_held) and bool(self.j_button_held)

                if both_held:
                    # Rising edge of the chord
                    if not self.prev_both_held:
                        self.both_press_t = t_now
                        self.both_long_triggered = False

                    # Check for long-hold → quit
                    if (self.both_press_t is not None and
                        not self.both_long_triggered and
                        (t_now - self.both_press_t) >= QUIT_HOLD_S):

                        self.both_long_triggered = True
                        notify(f"[Gesture] Both buttons held for {QUIT_HOLD_S:.1f}s → quitting & disconnecting…")
                        self.running = False
                        break  # exit main loop, cleanup will run after the loop

                    # WHILE BOTH BUTTONS ARE DOWN:
                    #  - cancel any tap/drag/zoom state
                    #  - do NOT let individual SPACE/J gesture logic run this frame
                    self.press_t = None
                    self.longpress_active = False
                    self.drag_active = False
                    self.space_pending_click = False
                    self.j_pending_rclick = False
                    self.tap_count = 0
                    self.j_last_tap_end = -1e9
                    self.space_spotlight_triggered = False
                    self.j_spotlight_triggered = False


                    # Keep edge detectors in sync so we don't generate fake edges later
                    self.prev_both_held = True
                    self.prev_btn = button_held
                    self.j_prev_btn = self.j_button_held
                    # Skip the rest of SPACE/J handling for this frame
                    continue

                # Here: both_held is False
                if self.prev_both_held:
                    # We JUST released a chord (both were held last frame)
                    duration = t_now - (self.both_press_t or t_now)

                    # Short chord (0.05–1.0 s) → calibration
                    if (self.both_press_t is not None and
                        not self.both_long_triggered and
                        0.05 <= duration <= 1.0):
                        notify("[Gesture] Both buttons quick chord → start calibration.")
                        self._start_interactive_calibration()

                    # Reset chord state
                    self.both_press_t = None
                    self.both_long_triggered = False
                    self.prev_both_held = False

                    # IMPORTANT:
                    # Suppress this frame's SPACE/J release from generating clicks,
                    # zooms, drags, etc. by "eating" the edge here.
                    self.prev_btn = button_held
                    self.j_prev_btn = self.j_button_held
                    continue

                # No chord this frame
                self.prev_both_held = False

                # ----- Interactive calibration wizard processing -----
                if self._interactive_calib_step(ax, ay, az, gx, gy, gz):
                    self.prev_btn = False
                    continue

                # --- Button edge detection and gesture logic (SPACE only) ---
                if button_held and not self.prev_btn:
                    # Rising edge: start possible tap/hold
                    self.press_t = t_now
                    self.longpress_active = False
                    self.next_zoom_tick = 0.0
                    self.space_annotate_triggered = False

                elif button_held and self.prev_btn:
                    # While holding SPACE: drag, spotlight, or long-press zoom OUT
                    if self.press_t is not None and not self.typing_mode:
                        hold_dur = t_now - self.press_t

                        # ---- LASER MODE: Hold SPACE ≥1.5s in Presentation mode to toggle laser pointer ----
                        if (
                            self.presentation_mode
                            and not self.space_annotate_triggered
                            and not self.annotation_active        # don't change laser while annotating
                            and not self.drag_active              # and NEVER while dragging/drawing
                            and hold_dur >= LASER_HOLD_MIN        # laser threshold
                            and hold_dur < LONG_PRESS_MIN         # don't collide with zoom window
                        ):

                            # If we somehow started a drag, end it cleanly
                            if self.drag_active:
                                try:
                                    pyautogui.mouseUp()
                                except Exception as e:
                                    notify(f"[Drag] mouseUp before laser toggle error: {e}")
                                self.drag_active = False

                            # Toggle laser pointer
                            self._toggle_laser_pointer()

                            # ✅ HARD-CANCEL any click/tap behavior for this press
                            self.space_annotate_triggered = True
                            self.press_t = None          # so release won't treat it as a tap
                            self.space_pending_click = False
                            self.pending_single_click = False
                            self.tap_count = 0
                            self.last_tap_end = -1e9

                            continue

                        # --- Drag vs long-press zoom-out (SPACE hold) ---
                        if not self.space_annotate_triggered:
                            # 1) Start drag (highlight / annotation) for medium hold
                            if (
                                (hold_dur > TAP_MAX_DURATION)
                                and (hold_dur < LONG_PRESS_MIN)
                                and (not self.drag_active)
                                and (not self.presentation_mode or self.annotation_active)
                                # ^ Only drag:
                                #   - in non-presentation modes, OR
                                #   - in Presentation when annotation is active
                            ):
                                try:
                                    pyautogui.mouseDown()
                                except Exception as e:
                                    print(f"[Drag] mouseDown error: {e}")
                                self.drag_active = True
                                self.pending_single_click = False  # no normal click now

                            # 2) Long-press → zoom out (>= LONG_PRESS_MIN)
                            elif (
                                (hold_dur >= LONG_PRESS_MIN)
                                and (hold_dur <= LONG_PRESS_MAX)
                                and (not self.longpress_active)
                            ):
                                if self.drag_active:
                                    try:
                                        pyautogui.mouseUp()
                                    except Exception as e:
                                        print(f"[Drag] mouseUp before zoom error: {e}")
                                    self.drag_active = False

                                self.longpress_active = True
                                self.next_zoom_tick = t_now
                                self.pending_single_click = False


                            # Long-press → zoom out (>= LONG_PRESS_MIN)
                            elif (hold_dur >= LONG_PRESS_MIN) and (hold_dur <= LONG_PRESS_MAX):
                                if self.drag_active:
                                    try:
                                        pyautogui.mouseUp()
                                    except Exception as e:
                                        print(f"[Drag] mouseUp before zoom error: {e}")
                                    self.drag_active = False

                                self.longpress_active = True
                                self.next_zoom_tick = t_now
                                self.pending_single_click = False

                        if self.longpress_active:
                            if hold_dur > LONG_PRESS_MAX:
                                self.longpress_active = False
                            elif t_now >= self.next_zoom_tick:
                                self._zoom_out_step()
                                self.next_zoom_tick += 1.0 / max(1e-6, ZOOM_HOLD_REPEAT_HZ)

                elif (not button_held) and self.prev_btn:
                    # Falling edge: classify tap / end drag / stop zoom
                    if self.press_t is not None:
                        hold_dur = t_now - self.press_t
                        # If this press already triggered annotation, just reset state
                        if self.space_annotate_triggered:
                            if self.drag_active:
                                try:
                                    pyautogui.mouseUp()
                                except Exception as e:
                                    print(f"[Drag] mouseUp after annotate error: {e}")
                                self.drag_active = False
                            self.longpress_active = False
                            self.press_t = None
                            self.space_annotate_triggered = False

                        else:
                            if self.longpress_active:
                                # Finished a long-press zoom-out
                                self.longpress_active = False

                            elif self.drag_active:
                                # Finish drag-based highlight
                                try:
                                    pyautogui.mouseUp()
                                except Exception as e:
                                    print(f"[Drag] mouseUp error: {e}")
                                self.drag_active = False

                            elif hold_dur <= TAP_MAX_DURATION:
                                # SHORT TAP: handle clustering first
                                if (t_now - self.last_tap_end) <= DOUBLE_CLICK_MAX_GAP:
                                    self.tap_count += 1
                                else:
                                    self.tap_count = 1
                                self.last_tap_end = t_now

                                if self.presentation_mode:
                                    # --- PRESENTATION MODE ---
                                    if self.tap_count == 2:
                                        # Double-tap LEFT → toggle annotation pen ONLY (no slide advance)
                                        self.space_pending_click = False  # cancel any pending single
                                        self._toggle_annotation()
                                        self.tap_count = 0
                                    else:
                                        # First tap: arm a pending single "NEXT slide" click
                                        self.space_pending_click = True
                                        self.space_single_deadline = t_now + DOUBLE_CLICK_MAX_GAP
                                else:
                                    # --- POINTER / TYPING MODES ---
                                    try:
                                        self._left_click_action()
                                    except Exception as e:
                                        print(f"[Click] click error: {e}")

                                    # Triple tap → zoom in (pointer mode only)
                                    if self.tap_count == 3 and not self.typing_mode:
                                        self._zoom_in_step()
                                        self.tap_count = 0

                        # Done with this press
                        self.press_t = None
                    # tap_count intentionally NOT reset here (we keep cluster info)

                # --- 'j' logic: tap = right click; double-tap = close/slideshow; holds = spotlight / mode toggle ---
                j_held = self.j_button_held

                # rising edge of 'j'
                if j_held and not self.j_prev_btn:
                    self.j_press_t = t_now
                    self.j_long_mode_triggered = False   # reset long-hold flag on new press
                    self.j_spotlight_triggered = False    # reset spotlight flag for this press

                # while 'j' is held
                if j_held and self.j_prev_btn and (self.j_press_t is not None):
                    j_hold_dur = t_now - self.j_press_t

                    # 2) Long hold ≥ J_MODE_HOLD_S → cycle modes
                    #    (only if we didn't already use this press for spotlight)
                    if (
                        not self.j_long_mode_triggered
                        and not self.j_spotlight_triggered
                        and j_hold_dur >= self.J_MODE_HOLD_S
                    ):
                        # Cycle modes: POINTER -> TYPING -> PRESENTATION -> POINTER ...
                        if self.presentation_mode:
                            next_mode = "pointer"
                        elif self.typing_mode:
                            next_mode = "presentation"
                        else:
                            next_mode = "typing"

                        self._set_mode(next_mode)

                        # Cancel any pending click gestures
                        self.j_long_mode_triggered = True
                        self.j_pending_rclick = False

                        # Cancel any pending click gestures
                        self.j_long_mode_triggered = True
                        self.j_pending_rclick = False

                # falling edge of 'j'
                if (not j_held) and self.j_prev_btn:
                    if self.j_press_t is not None:
                        j_hold_dur = t_now - self.j_press_t

                        # Only treat as tap if we did NOT use this press for mode toggle or spotlight
                        if not self.j_long_mode_triggered and not self.j_spotlight_triggered:
                            if j_hold_dur <= self.J_TAP_MAX_DURATION:
                                if (t_now - self.j_last_tap_end) <= self.J_DOUBLE_GAP:
                                    # DOUBLE-TAP
                                    self.j_pending_rclick = False  # cancel pending single
                                    self.j_last_tap_end = t_now

                                    if self.typing_mode:
                                        # In TYPING mode → toggle submodes
                                        self.dwell_submode = not self.dwell_submode
                                        sub = "DWELL-to-type" if self.dwell_submode else "CLICK-to-type"
                                        notify(f"[Mode] TYPING submode changed → {sub}.")
                                    elif self.presentation_mode:
                                        # In PRESENTATION mode → toggle slideshow on/off
                                        notify(f"[Presentation] J double-tap: slideshow_running={self.slideshow_running}")
                                        if self.slideshow_running:
                                            # We think a slideshow is currently running → exit cleanly
                                            app = self._detect_presentation_app()
                                            try:
                                                # For PowerPoint, first leave ink/pen mode so we don't get the "Save annotations?" dialog
                                                if app == "ppt":
                                                    if sys.platform == "darwin":
                                                        pyautogui.hotkey("command", "a")  # switch to arrow tool on Mac
                                                    else:
                                                        pyautogui.hotkey("ctrl", "a")     # switch to arrow tool on Windows
                                                    time.sleep(0.05)                      # tiny delay so PowerPoint registers it

                                                # Now exit slideshow
                                                pyautogui.press("esc")
                                                notify("[Presentation] Exited slideshow.", blocking=False)
                                            except Exception as e:
                                                notify(f"[Presentation] Error exiting slideshow: {e}", blocking=False)

                                            self.slideshow_running = False

                                            # 👇 set up a short watch window for the PPT annotation dialog
                                            self._modal_prev_mode = (
                                                "presentation" if self.presentation_mode
                                                else ("typing" if self.typing_mode else "pointer")
                                            )
                                            self._modal_watch_until = time.time() + 1.0  # watch ~4 seconds
                                            self._modal_active = False

                                        else:
                                            # We think slideshow is OFF → try to start it for the active app
                                            app = self._detect_presentation_app()
                                            notify(f"[Presentation] J double-tap: starting slideshow for app={app}")

                                            if app == "slides":
                                                self._start_slides_slideshow()
                                                self.slideshow_running = True
                                            elif app == "ppt":
                                                self._start_powerpoint_slideshow()
                                                self.slideshow_running = True
                                            else:
                                                notify("[Presentation] Double-tap J, but no Slides/PowerPoint window detected.")

                                    else:
                                        # In POINTER mode → double-tap J closes active window
                                        self._close_active_window()

                                else:
                                    # first tap → arm pending right-click
                                    self.j_pending_rclick = True
                                    self.j_single_deadline = t_now + self.J_DOUBLE_GAP
                                    self.j_last_tap_end = t_now

                    self.j_press_t = None
                    self.j_long_mode_triggered = False
                    self.j_spotlight_triggered = False

                # if a second tap didn't arrive in time, issue the right-click (or next slide)
                if self.j_pending_rclick and (t_now >= self.j_single_deadline):
                    self._right_click_action()
                    self.j_pending_rclick = False

                # remember for next loop
                self.j_prev_btn = j_held

                # If we armed a single-tap in Presentation mode and the gap passed
                if self.presentation_mode and self.space_pending_click and (t_now >= self.space_single_deadline):
                    # Confirmed single tap → advance slide once
                    try:
                        self._left_click_action()
                    except Exception as e:
                        print(f"[Click] pending click error: {e}")
                    self.space_pending_click = False
                    self.tap_count = 0

                # Update previous button state
                self.prev_btn = button_held

                # While left button is held, disable drift corrections but DO NOT freeze cursor
                if button_held:
                    self.drift_still_time = 0.0
                    self.drift_last_stable_pos = pyautogui.position()

                # ----- cursor control (continuous, world-aligned) -----
                # Typing Mode → 40% slower (60% of normal gain)
                speed_factor = 0.6 if self.typing_mode else 1.0

                # Heavier smoothing in Typing Mode (smaller alpha → more smoothing)
                if self.typing_mode:
                    current_alpha = EMA_ALPHA * 0.6   # e.g., 0.25 → 0.15
                else:
                    current_alpha = EMA_ALPHA
                self.ema_vx.set_alpha(current_alpha)
                self.ema_vy.set_alpha(current_alpha)

                ACCEL_SCALE = 0.02 * speed_factor  # base gain scaled by mode

                a_cal = self.R_s2w @ np.array([ax, ay, az], dtype=float)  # rotate accel into world frame
                dx = self.ema_vx.update(SENS_X * DIR_X * (-a_cal[0]) * ACCEL_SCALE)  # left/right tilt
                dy = self.ema_vy.update(SENS_Y * DIR_Y * (-a_cal[1]) * ACCEL_SCALE)  # forward/back tilt

                # --- Rehab metrics update (background, all modes) ---
                if self.rehab_session_active:
                    self._rehab_update_metrics(a_cal, gx, gy, gz, t_now)

                # clamp per-tick
                dx = max(-MAX_STEP, min(MAX_STEP, dx))
                dy = max(-MAX_STEP, min(MAX_STEP, dy))

                if dx or dy:
                    # current position and screen bounds
                    x, y = pyautogui.position()
                    sw, sh = pyautogui.size()
                    # proposed target (invert Y for screen feel)
                    tx = x + dx
                    ty = y - dy

                    tx = max(0, min(sw - 1, tx))
                    ty = max(0, min(sh - 1, ty))
                    try:
                        pyautogui.moveTo(tx, ty, duration=0)
                    except pyautogui.FailSafeException:
                        # Recover gracefully if we ever hit a corner
                        w, h = pyautogui.size()
                        pyautogui.moveTo(w/2, h/2, duration=0.15)
                        self.ema_vx.reset(0.0)
                        self.ema_vy.reset(0.0)
                        print("[Recover] Fail-safe hit. Re-centered and continued.")

                # --- HUD: update direction arrow ---
                if getattr(self, "hud", None) is not None:
                    try:
                        self.hud.set_direction(dx, dy)
                    except Exception as e:
                        print(f"[HUD] set_direction error: {e}")

                # ----- Typing-mode dwell-to-type submode -----
                if self.typing_mode and self.dwell_submode and (not button_held):
                    cx, cy = pyautogui.position()

                    if self.dwell_anchor_pos is None:
                        # first time or after leaving a key region
                        self.dwell_anchor_pos = (cx, cy)
                        self.dwell_start_t = t_now
                        self.dwell_fired = False
                    else:
                        ax0, ay0 = self.dwell_anchor_pos
                        dist = math.hypot(cx - ax0, cy - ay0)

                        if dist > self.DWELL_MOVE_THRESH:
                            # moved to a new key/area → start a new dwell
                            self.dwell_anchor_pos = (cx, cy)
                            self.dwell_start_t = t_now
                            self.dwell_fired = False
                        else:
                            # still on same key
                            if (
                                not self.dwell_fired
                                and self.dwell_start_t is not None
                                and (t_now - self.dwell_start_t) >= self.DWELL_TRIGGER_S
                            ):
                                pyautogui.click()
                                self.dwell_fired = True
                else:
                    # leaving dwell mode or leaving typing mode → reset dwell state
                    self.dwell_anchor_pos = None
                    self.dwell_start_t = None
                    self.dwell_fired = False

                # ----- Typing-mode drift stabilization -----
                if self.typing_mode:
                    # Use gyro magnitude as a proxy for motion
                    gyro_mag = math.sqrt(gx*gx + gy*gy + gz*gz)

                    if gyro_mag < self.DRIFT_MOTION_THRESH:
                        # Ring is "still"
                        self.drift_still_time += 1.0 / FS_HZ
                    else:
                        # User is moving → reset still timer and update stable point
                        self.drift_still_time = 0.0
                        self.drift_last_stable_pos = pyautogui.position()

                    if (self.drift_still_time >= self.DRIFT_STILL_TIME_S and
                        self.drift_last_stable_pos is not None):

                        # Gently nudge cursor toward last stable point
                        cx, cy = pyautogui.position()
                        tx, ty = self.drift_last_stable_pos

                        alpha = self.DRIFT_NUDGE_ALPHA
                        new_x = cx + alpha * (tx - cx)
                        new_y = cy + alpha * (ty - cy)

                        # keep away from edges (reuse SAFE_MARGIN + screen size)
                        sw, sh = pyautogui.size()
                        new_x = max(SAFE_MARGIN, min(sw - 1 - SAFE_MARGIN, new_x))
                        new_y = max(SAFE_MARGIN, min(sh - 1 - SAFE_MARGIN, new_y))

                        try:
                            pyautogui.moveTo(new_x, new_y, duration=0)
                        except pyautogui.FailSafeException:
                            w, h = pyautogui.size()
                            pyautogui.moveTo(w/2, h/2, duration=0.15)
                            self.ema_vx.reset(0.0)
                            self.ema_vy.reset(0.0)
                            print("[Recover] Fail-safe hit during drift correction. Re-centered and continued.")
                else:
                    # Not in typing mode → no drift logic
                    self.drift_still_time = 0.0
                    self.drift_last_stable_pos = None

            except Exception as e:
                print(f"[Loop] ERROR: {e}")
                time.sleep(0.02)

        # Finish and save background rehab session
        try:
            self._end_rehab_session()
        except Exception as e:
            print(f"[Rehab] Error finalizing session: {e}")

        # cleanup
        try:
            if ZOOM_METHOD == 'wheel':
                self._ensure_mod_up()
        except Exception:
            pass
        try:
            if self.ser:
                self.ser.close()
        except Exception:
            pass
        try:
            if self.ring:
                self.ring.stop()
        except Exception:
            pass
        try:
            listener.stop()
        except Exception:
            pass
        notify("EngineeRing disconnected. Bye.", blocking=True)

# ===================== ENTRY ===================== # 
def main():

    # Silent (console-only) startup info
    if not USE_BLE:
        print(f"[Serial] {PORT} @ {BAUD}")
    if USE_BLE:
        print(f"[BLE] {'auto-discover' if BLE_ADDRESS is None else BLE_ADDRESS} (Nordic UART Service)")

    launch_osk = False  # Reflect OS + chosen zoom method
    zoom_in_label = "SPACE"
    zoom_out_label = "SPACE"


    app = IMU2MouseApp(
        PORT, BAUD,
        launch_osk=launch_osk,
        use_ble=USE_BLE,
        ble_address=BLE_ADDRESS
    )
    try:
        app.run()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
