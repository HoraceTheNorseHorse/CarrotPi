"""
Haptic feedback via a 5 V vibration module wired to a GPIO pin.

The module is driven high for PULSE_MS milliseconds on every button press.
Uses RPi.GPIO; fails silently on platforms where it is unavailable (e.g. macOS).

Change HAPTIC_PIN to match your wiring.
"""

import threading

HAPTIC_PIN  = 17          # BCM pin number — adjust to match wiring
PULSE_MS    = 40          # vibration pulse length in milliseconds

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(HAPTIC_PIN, GPIO.OUT, initial=GPIO.LOW)
    _AVAILABLE = True
except Exception:
    GPIO = None
    _AVAILABLE = False


def buzz() -> None:
    """Fire a single haptic pulse. Non-blocking — runs on a daemon thread."""
    if not _AVAILABLE:
        return
    threading.Thread(target=_pulse, daemon=True).start()


def _pulse() -> None:
    try:
        GPIO.output(HAPTIC_PIN, GPIO.HIGH)
        import time
        time.sleep(PULSE_MS / 1000)
        GPIO.output(HAPTIC_PIN, GPIO.LOW)
    except Exception:
        pass
