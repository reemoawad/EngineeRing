# ring_ble_input.py
import asyncio
import struct
from bleak import BleakClient, BleakScanner
from collections import deque
import threading
import time

# Nordic UART Service (NUS)
NUS_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
NUS_RX_UUID      = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"  # write (unused)
NUS_TX_UUID      = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"  # notify

class RingBLEInput:
    """
    Bridges BLE notifications -> queue you can poll from your main loop.
    Each sample: {
      "t": epoch_seconds,
      "b1": int, "b2": int,
      "ax": int16, "ay": int16, "az": int16,
      "gx": int16, "gy": int16, "gz": int16
    }
    """
    def __init__(self, device_name_contains="", address=None):
        self.device_name_contains = device_name_contains
        self.address = address
        self._queue = deque(maxlen=512)
        self._loop = None
        self._client = None
        self._thread = None
        self._connected_evt = threading.Event()
        self._stop_evt = threading.Event()

    def _handle_notify(self, _handle, data: bytearray):
        # Expect: 2 button bytes + 6 * int16 big-endian = 14 bytes
        if len(data) < 14:
            return
        b1, b2 = data[0], data[1]
        ax, ay, az, gx, gy, gz = struct.unpack(">6h", data[2:14])
        self._queue.append({
            "t": time.time(),
            "b1": b1, "b2": b2,
            "ax": ax, "ay": ay, "az": az,
            "gx": gx, "gy": gy, "gz": gz,
        })

    async def _connect_and_listen(self):
        target = self.address

        # --- Discover if no explicit address was provided ---
        if target is None:
            cand = None
            try:
                def _match(device, adv):
                    name_ok = False
                    if self.device_name_contains:
                        n = (device.name or "").lower()
                        name_ok = self.device_name_contains.lower() in n
                    uuids = []
                    if adv is not None and getattr(adv, "service_uuids", None):
                        uuids = [u.lower() for u in (adv.service_uuids or [])]
                    uuid_ok = (NUS_SERVICE_UUID.lower() in uuids)
                    return uuid_ok or name_ok

                cand = await BleakScanner.find_device_by_filter(_match, timeout=10.0)
            except Exception:
                cand = None

            if cand is None:
                devices = await BleakScanner.discover(timeout=10.0)
                for d in devices:
                    name = (getattr(d, "name", "") or "").lower()
                    if self.device_name_contains and self.device_name_contains.lower() in name:
                        cand = d
                        break
                    md = getattr(d, "metadata", None)
                    if isinstance(md, dict):
                        uuids = [u.lower() for u in md.get("uuids", []) if u]
                        if NUS_SERVICE_UUID.lower() in uuids:
                            cand = d
                            break

            if not cand:
                raise RuntimeError("Ring not found over BLE. Turn it on and try again.")
            target = cand.address  # <- discovered address

        # --- Connect and stream (runs whether we discovered OR had an address) ---
        try:
            print(f"[RingBLEInput] Connecting to {target} …")
            async with BleakClient(target) as client:
                if not client.is_connected:
                    raise RuntimeError("Failed to connect to ring.")
                print("[RingBLEInput] Connected. Starting notify…")
                await client.start_notify(NUS_TX_UUID, self._handle_notify)
                self._connected_evt.set()
                try:
                    while not self._stop_evt.is_set():
                        await asyncio.sleep(0.05)
                finally:
                    try:
                        await client.stop_notify(NUS_TX_UUID)
                    except Exception:
                        pass
                    print("[RingBLEInput] Stopped notify, exiting loop.")
        except Exception as e:
            print(f"[RingBLEInput] Connect/listen error: {e}")
            raise

    def _runner(self):
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._connect_and_listen())
        except Exception as e:
            # Do NOT set connected event here; it masks failures
            print(f"[RingBLEInput] Error: {e}")

    def start(self, timeout=10.0):
        self._stop_evt.clear()
        self._thread = threading.Thread(target=self._runner, daemon=True)
        self._thread.start()
        if not self._connected_evt.wait(timeout=timeout):
            raise TimeoutError("Timeout waiting for BLE connection.")

    def stop(self):
        self._stop_evt.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    def read(self):
        """Return latest sample or None (non-blocking-ish)."""
        return self._queue[-1] if self._queue else None
