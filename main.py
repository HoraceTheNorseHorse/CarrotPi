import sys
sys.argv += ['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']

import os
from datetime import datetime

# Chromium flags for QtWebEngine — must be set before any Qt import.
# --no-sandbox: required on macOS to allow network access from the Chromium
#   renderer process; without it outbound connections silently fail.
# --disable-gpu: kills the GPU process and its display compositor, which
#   crashes on macOS with SharedImageManager mailbox errors.
# --disable-gpu-compositing: prevents GPU compositor starting independently.
# The QtWebEngineProcess subprocess requires com.apple.security.cs.allow-jit
# to JIT-compile JS on macOS. The CLT Python binary ships without it, causing
# SIGABRT (exit 134) when Maps fires JS. Fix: re-sign the Python binary once:
#   sudo codesign --force --sign - \
#     --entitlements /tmp/carrotpi-jit.plist \
#     /Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/bin/python3.9
# (see CLAUDE.md or project notes for the full entitlements plist)
os.environ.setdefault(
    "QTWEBENGINE_CHROMIUM_FLAGS",
    "--no-sandbox --disable-gpu --disable-gpu-compositing"
)

# QtWebEngineWidgets MUST be imported before QApplication is instantiated.
# Importing the maps module here satisfies that requirement on both Mac and Pi.
from pages.maps import MapsPage
from pages.spotify import SpotifyPage
from pages.weather import WeatherPage
from pages.volume import VolumeOverlay

from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QWidget, QPushButton
from PyQt5.QtGui import QPixmap, QColor, QPainter, QFont
from PyQt5.QtCore import Qt, QRect, QTimer

import hardware.relays as relays
import hardware.haptic  as haptic

ASSETS = "./assets"

# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------

# Panel definitions: (filename, x, y, w, h, placeholder_color)
PANELS = [
    ("left_switches.png",  0,    0, 327,  600, QColor(40,  40,  60)),
    ("center_panel.png",   328,  0, 1147, 600, QColor(25,  25,  35)),
    ("right_buttons.png",  1476, 0, 124,  600, QColor(40,  40,  60)),
]

# Overlay definitions: key → (filename, x, y, w, h, placeholder_color)
# Placeholder colors are semi-transparent so the panel beneath shows through.
OVERLAYS = {
    "defrost_on":    ("defrost_on.png",    0,   187, 327, 123, QColor(0,   180, 255,  90)),
    "hazards_on":    ("hazards_on.png",    0,   311, 327, 122, QColor(255, 160,   0,  90)),
    "hazards_flash": ("hazards_flash.png", 0,   311, 327, 122, QColor(255,  80,   0, 140)),
    "home_off":      ("home_off.png",      0,   433, 327, 167, QColor(120, 120, 150,  90)),
    "fan_1":         ("fan_1.png",         332, 340, 218, 260, QColor( 80, 200,  80,  90)),
    "fan_2":         ("fan_2.png",         332, 340, 218, 260, QColor(140, 220,  80,  90)),
    "fan_3":         ("fan_3.png",         332, 340, 218, 260, QColor(200, 255,  80,  90)),
    # HVAC overlays — position x=554, y=330; real sizes vary per image so the
    # placeholder uses a reasonable stand-in; actual PNGs will override at load.
    "hvac_2":        ("hvac_2.png",        554, 330, 720, 220, QColor( 60, 160, 200,  90)),
    "hvac_3":        ("hvac_3.png",        554, 330, 720, 220, QColor( 60, 200, 200,  90)),
    "hvac_4":        ("hvac_4.png",        554, 330, 720, 220, QColor( 60, 120, 180,  90)),
    "hvac_5":        ("hvac_5.png",        554, 330, 720, 220, QColor(220, 100,  60,  90)),
    "hvac_6":        ("hvac_6.png",        554, 330, 720, 220, QColor(220, 140,  60,  90)),
    "hvac_7":        ("hvac_7.png",        554, 330, 720, 220, QColor(200,  80,  40,  90)),
    "hvac_8":        ("hvac_8.png",        554, 330, 720, 220, QColor(220, 120,  40,  90)),
}

# HVAC overlay lookup: (temp, floor, hvacdef) → overlay key, or None for no overlay.
# Mirrors the HVAC image table in CLAUDE.md exactly.
HVAC_TABLE = {
    ("cold", "on",  "off"): None,       # default — center_panel.png only
    ("cold", "off", "on" ): "hvac_2",
    ("cold", "on",  "on" ): "hvac_3",
    ("cold", "off", "off"): "hvac_4",
    ("hot",  "off", "on" ): "hvac_5",
    ("hot",  "on",  "on" ): "hvac_6",
    ("hot",  "off", "off"): "hvac_7",
    ("hot",  "on",  "off"): "hvac_8",
}

HVAC_OVERLAY_KEYS = [k for k in OVERLAYS if k.startswith("hvac_")]

# Button hit zones: (name, x1, y1, x2, y2)  — absolute in 1600×600 window
BUTTONS = [
    # Left panel
    ("gti",             88,   70,  240, 160),
    ("defrost_switch",  88,  193,  240, 280),
    ("hazards_switch",  88,  317,  240, 402),
    ("home_switch",     88,  437,  240, 525),

    # Center panel
    ("fan_switch",     372,  452,  492, 567),
    ("volume",         384,   88,  536, 250),
    ("tuner",         1260,   88, 1413, 250),
    ("preset_1",       620,  210,  702, 260),
    ("preset_2",       730,  210,  820, 260),
    ("preset_3",       855,  210,  941, 260),
    ("preset_4",       972,  210, 1062, 260),
    ("preset_5",      1086,  210, 1175, 260),
    ("floor_left",     562,  375,  703, 440),
    ("floor_right",    873,  375,  960, 440),
    ("def_left",      1021,  375, 1121, 440),
    ("def_right",     1300,  375, 1420, 440),
    ("temp_left",      562,  488,  703, 562),
    ("temp_right",    1300,  488, 1420, 562),

    # Right panel
    ("right_button_1", 1476,   0, 1600, 123),
    ("right_button_2", 1476, 123, 1600, 242),
    ("right_button_3", 1476, 242, 1600, 362),
    ("right_button_4", 1476, 362, 1600, 480),
    ("right_button_5", 1476, 480, 1600, 600),
]

# Relay assignments per state (from CLAUDE.md)
RELAY_DEFROST  = 1
RELAY_HAZARDS  = 2
RELAY_FAN_1    = 3
RELAY_FAN_2    = 4
RELAY_FAN_3    = 5

_BTN_STYLE = """
    QPushButton {
        background: transparent;
        border: none;
    }
    QPushButton:pressed {
        background: rgba(255, 255, 255, 20);
    }
"""

# right_button_5 zone — clock lives here
CLOCK_X, CLOCK_Y, CLOCK_W, CLOCK_H = 1476, 480, 124, 120

# ---------------------------------------------------------------------------
# Default application state
# ---------------------------------------------------------------------------

DEFAULT_STATE = {
    "mode":    "light",
    "defrost": "off",
    "hazards": "off",
    "home":    "on",
    "fan":     0,
    "floor":   "on",
    "temp":    "cold",
    "hvacdef": "off",
    "maps":    "off",
    "spotify": "off",
    "weather": "off",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_pixmap(filename, w, h, placeholder_color):
    """Return a QPixmap from assets/, or a labelled placeholder if missing."""
    path = os.path.join(ASSETS, filename)
    if os.path.exists(path):
        return QPixmap(path)
    px = QPixmap(w, h)
    px.fill(placeholder_color)
    painter = QPainter(px)
    painter.setPen(QColor(200, 200, 220))
    painter.drawText(QRect(0, 0, w, h), Qt.AlignCenter, filename)
    painter.end()
    return px


def _make_label(parent, x, y, w, h):
    """Create a transparent QLabel positioned at (x, y) sized (w×h)."""
    lbl = QLabel(parent)
    lbl.setGeometry(x, y, w, h)
    lbl.setScaledContents(True)
    lbl.setAttribute(Qt.WA_TranslucentBackground)
    return lbl


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class CarrotPi(QMainWindow):

    def __init__(self):
        super().__init__()
        self.state = dict(DEFAULT_STATE)

        # QTimer for hazard flasher
        self._hazard_flash_state = False          # False = hazards_on, True = hazards_flash
        self._hazard_timer = QTimer(self)
        self._hazard_timer.setInterval(500)
        self._hazard_timer.timeout.connect(self._tick_hazard_flash)

        # Clock — even ticks show colon, odd ticks hide it
        self._clock_tick = False
        self._clock_timer = QTimer(self)
        self._clock_timer.setInterval(500)
        self._clock_timer.timeout.connect(self._tick_clock)

        self._init_ui()
        self._clock_timer.start()
        self._tick_clock()          # render immediately, don't wait 500 ms

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _init_ui(self):
        self.setWindowTitle("CarrotPi")
        self.setFixedSize(1600, 600)
        self.setWindowFlags(Qt.FramelessWindowHint)

        canvas = QWidget(self)
        canvas.setGeometry(0, 0, 1600, 600)
        canvas.setStyleSheet("background: black;")
        self.setCentralWidget(canvas)

        # 1. Base panels
        self.panels = {}
        for filename, x, y, w, h, color in PANELS:
            lbl = _make_label(canvas, x, y, w, h)
            lbl.setPixmap(_load_pixmap(filename, w, h, color))
            self.panels[filename.replace(".png", "")] = lbl

        # 2. Overlay labels — all hidden at startup
        self.overlays = {}
        for key, (filename, x, y, w, h, color) in OVERLAYS.items():
            lbl = _make_label(canvas, x, y, w, h)
            lbl.setPixmap(_load_pixmap(filename, w, h, color))
            lbl.hide()
            self.overlays[key] = lbl

        # 3. Pages (constructed here so they share the canvas; hidden by default)
        self.maps_page     = MapsPage(canvas)
        self.spotify_page  = SpotifyPage(canvas)
        self.weather_page  = WeatherPage(canvas)

        # 4. Clock display — inside right_button_5 zone, below button layer
        self._clock_label = QLabel(canvas)
        self._clock_label.setGeometry(CLOCK_X, CLOCK_Y, CLOCK_W, CLOCK_H)
        self._clock_label.setAlignment(Qt.AlignCenter)
        self._clock_label.setAttribute(Qt.WA_TranslucentBackground)
        # Two stacked lines: time on top, AM/PM below
        time_font = QFont("Helvetica Neue", 26, QFont.Bold)
        self._clock_label.setFont(time_font)
        self._clock_label.setStyleSheet("color: white; background: transparent;")

        # 5. Transparent button overlays (topmost so they receive clicks)
        self.buttons = {}
        for name, x1, y1, x2, y2 in BUTTONS:
            btn = QPushButton(canvas)
            btn.setGeometry(x1, y1, x2 - x1, y2 - y1)
            btn.setStyleSheet(_BTN_STYLE)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(self._make_handler(name))
            self.buttons[name] = btn

        # 6. Volume overlay — constructed last so raise_() always brings it to top
        self._volume_overlay = VolumeOverlay(canvas)

    # ------------------------------------------------------------------
    # Button dispatch
    # ------------------------------------------------------------------

    def _make_handler(self, name):
        """Return a slot bound to this button name."""
        def handler():
            self._on_button(name)
        return handler

    def _on_button(self, name):
        haptic.buzz()

        dispatch = {
            "defrost_switch": self._press_defrost,
            "hazards_switch": self._press_hazards,
            "fan_switch":     self._press_fan,
            "home_switch":    self._press_home,
            "floor_left":     self._press_floor,
            "floor_right":    self._press_floor,
            "def_left":       self._press_hvacdef,
            "def_right":      self._press_hvacdef,
            "temp_left":      self._press_temp,
            "temp_right":     self._press_temp,
            "volume":         self._press_volume,
            "right_button_1": lambda: print("[button] right_button_1 — WiFi (not yet implemented)"),
            "right_button_2": self._press_maps,
            "right_button_3": self._press_spotify,
            "right_button_4": lambda: print("[button] right_button_4 — CarPlay/Android Auto (not yet implemented)"),
            "right_button_5": self._press_weather,
            "gti":            QApplication.quit,
        }

        action = dispatch.get(name)
        if action:
            action()
        else:
            print(f"[button] {name} (not yet implemented)")

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _press_defrost(self):
        on = self.state["defrost"] == "off"          # toggling to new value
        self.state["defrost"] = "on" if on else "off"

        if on:
            relays.relay_on(RELAY_DEFROST)
            self.overlays["defrost_on"].show()
        else:
            relays.relay_off(RELAY_DEFROST)
            self.overlays["defrost_on"].hide()

        print(f"[state] defrost → {self.state['defrost']}")

    def _press_hazards(self):
        on = self.state["hazards"] == "off"
        self.state["hazards"] = "on" if on else "off"

        if on:
            relays.relay_on(RELAY_HAZARDS)
            self._hazard_flash_state = False
            self.overlays["hazards_on"].show()
            self.overlays["hazards_flash"].hide()
            self._hazard_timer.start()
        else:
            relays.relay_off(RELAY_HAZARDS)
            self._hazard_timer.stop()
            self.overlays["hazards_on"].hide()
            self.overlays["hazards_flash"].hide()

        print(f"[state] hazards → {self.state['hazards']}")

    def _tick_clock(self):
        """Update clock label every 500 ms; blink colon on even ticks."""
        self._clock_tick = not self._clock_tick
        now  = datetime.now()
        hour = now.strftime("%I").lstrip("0") or "12"   # no leading zero, midnight = 12
        mins = now.strftime("%M")
        ampm = now.strftime("%p")
        sep  = ":" if self._clock_tick else " "
        # Rich-text lets us size AM/PM independently without a second label
        self._clock_label.setText(
            f"<span style='font-size:26pt; font-weight:700;'>{hour}{sep}{mins}</span>"
            f"<br><span style='font-size:11pt; font-weight:400; color:#aaaaaa;'>{ampm}</span>"
        )

    def _tick_hazard_flash(self):
        """Alternate between hazards_on and hazards_flash every 500 ms."""
        self._hazard_flash_state = not self._hazard_flash_state
        if self._hazard_flash_state:
            self.overlays["hazards_on"].hide()
            self.overlays["hazards_flash"].show()
        else:
            self.overlays["hazards_flash"].hide()
            self.overlays["hazards_on"].show()

    def _press_fan(self):
        # Cycle 0 → 1 → 2 → 3 → 0
        prev = self.state["fan"]
        nxt  = (prev + 1) % 4
        self.state["fan"] = nxt

        # Turn off all fan relays then activate the right one
        relays.relay_off(RELAY_FAN_1)
        relays.relay_off(RELAY_FAN_2)
        relays.relay_off(RELAY_FAN_3)

        relay_map = {1: RELAY_FAN_1, 2: RELAY_FAN_2, 3: RELAY_FAN_3}
        if nxt in relay_map:
            relays.relay_on(relay_map[nxt])

        # Show only the matching fan overlay
        for key in ("fan_1", "fan_2", "fan_3"):
            self.overlays[key].hide()
        if nxt > 0:
            self.overlays[f"fan_{nxt}"].show()

        print(f"[state] fan → {nxt}")

    def _press_floor(self):
        self.state["floor"] = "off" if self.state["floor"] == "on" else "on"
        print(f"[state] floor → {self.state['floor']}")
        self._update_hvac_overlay()

    def _press_hvacdef(self):
        self.state["hvacdef"] = "off" if self.state["hvacdef"] == "on" else "on"
        print(f"[state] hvacdef → {self.state['hvacdef']}")
        self._update_hvac_overlay()

    def _press_temp(self):
        self.state["temp"] = "hot" if self.state["temp"] == "cold" else "cold"
        print(f"[state] temp → {self.state['temp']}")
        self._update_hvac_overlay()

    def _update_hvac_overlay(self):
        """Evaluate temp/floor/hvacdef and show the correct hvac_N overlay."""
        key = HVAC_TABLE.get(
            (self.state["temp"], self.state["floor"], self.state["hvacdef"])
        )
        for k in HVAC_OVERLAY_KEYS:
            self.overlays[k].hide()
        if key:
            self.overlays[key].show()
        print(f"[hvac] overlay → {key or 'none'}")

    # ------------------------------------------------------------------
    # Shared helper — open a full-screen page, hiding panels + other pages
    # ------------------------------------------------------------------

    _CENTER_RIGHT_BUTTONS = {
        "fan_switch", "volume", "tuner",
        "preset_1", "preset_2", "preset_3", "preset_4", "preset_5",
        "floor_left", "floor_right", "def_left", "def_right",
        "temp_left", "temp_right",
        "right_button_1", "right_button_2", "right_button_3", "right_button_4",
        # right_button_5 is clock-only — no tap action, no need to disable
    }

    def _open_page(self, state_key):
        """Hide panels, disable buttons, show home_off. Cancel any other page."""
        self.state[state_key] = "on"
        self.state["home"]    = "off"

        # Cancel whichever other page might be open
        for key, page in (("maps", self.maps_page), ("spotify", self.spotify_page)):
            if key != state_key:
                self.state[key] = "off"
                page.hide_page()

        self.panels["center_panel"].hide()
        self.panels["right_buttons"].hide()
        self.overlays["home_off"].show()

        for name in self._CENTER_RIGHT_BUTTONS:
            self.buttons[name].setEnabled(False)

    def _press_maps(self):
        if self.state["maps"] == "on":
            return
        self._open_page("maps")
        self.maps_page.show_page()
        print("[state] maps → on")

    def _press_spotify(self):
        if self.state["spotify"] == "on":
            return
        self._open_page("spotify")
        self.spotify_page.show_page()
        print("[state] spotify → on")

    def _press_volume(self):
        self._volume_overlay.show_overlay()

    def _press_weather(self):
        if self.state["weather"] == "off":
            # If a full-page takeover (maps/spotify) is open, close it cleanly
            # so right_buttons is restored before weather takes center_panel.
            if self.state["maps"] == "on" or self.state["spotify"] == "on":
                self._press_home()
            self.state["weather"] = "on"
            self.panels["center_panel"].hide()
            self.weather_page.show_page()
            print("[state] weather → on")
        else:
            self._close_weather()

    def _close_weather(self):
        self.state["weather"] = "off"
        self.weather_page.hide_page()
        self.panels["center_panel"].show()
        print("[state] weather → off")

    def _press_home(self):
        # Always dismiss weather first (weather doesn't change home state,
        # so the guard below would incorrectly no-op while weather is visible)
        if self.state["weather"] == "on":
            self._close_weather()
            return

        if self.state["home"] == "on":
            print("[button] home_switch (already home — ignored)")
            return

        self.state["home"]    = "on"
        self.state["maps"]    = "off"
        self.state["spotify"] = "off"

        # Restore panels
        self.panels["center_panel"].show()
        self.panels["right_buttons"].show()
        self.overlays["home_off"].hide()

        # Re-enable all buttons
        for btn in self.buttons.values():
            btn.setEnabled(True)

        # Tear down any active page
        self.maps_page.hide_page()
        self.spotify_page.hide_page()

        print("[state] home → on")

    # ------------------------------------------------------------------
    # Keyboard shortcut (dev only)
    # ------------------------------------------------------------------

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Q:
            QApplication.quit()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    app = QApplication(sys.argv)
    window = CarrotPi()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
