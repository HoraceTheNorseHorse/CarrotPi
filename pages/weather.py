"""
pages/weather.py — NWS weather page (center panel only).

Geometry: x=328, y=0, w=1147, h=600  — right_buttons.png stays visible.

Uses the free National Weather Service API (no key required):
  Step 1: GET https://api.weather.gov/points/{lat},{lon}
          → returns .properties.forecast URL (unique to the grid cell)
  Step 2: GET {forecast_url}
          → returns .properties.periods[]

HTTP runs in a QThread so the UI never freezes.
show_page() triggers a fresh fetch every time it is called.
hide_page() hides the widget.

Lat/lon read from config.ini [weather]:
  lat           = 40.0639
  lon           = -80.7209
  contact_email = you@example.com   (included in User-Agent per NWS policy)
"""

import os
import json
import configparser
import urllib.request

from PyQt5.QtWidgets import QWidget, QLabel
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QThread, pyqtSignal

_HERE     = os.path.dirname(__file__)
_CFG_PATH = os.path.join(_HERE, "..", "config.ini")

WEATHER_X = 328
WEATHER_Y = 0
WEATHER_W = 1147
WEATHER_H = 600

_DEFAULT_LAT   = 40.0639
_DEFAULT_LON   = -80.7209
_DEFAULT_EMAIL = "carrotpi@example.com"

# How many forecast periods to display (the NWS returns ~14)
_NUM_PERIODS = 5


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def _read_weather_config():
    cfg = configparser.ConfigParser()
    cfg.read(_CFG_PATH)
    lat   = cfg.getfloat("weather", "lat",           fallback=_DEFAULT_LAT)
    lon   = cfg.getfloat("weather", "lon",           fallback=_DEFAULT_LON)
    email = cfg.get     ("weather", "contact_email", fallback=_DEFAULT_EMAIL)
    return lat, lon, email


# ---------------------------------------------------------------------------
# QThread — two-step NWS fetch
# ---------------------------------------------------------------------------

class WeatherFetcher(QThread):
    """
    Fetches NWS forecast data off the main thread.

    Signals:
      finished(list)  — list of period dicts from .properties.periods[]
      error(str)      — human-readable error message
    """

    finished = pyqtSignal(list)
    error    = pyqtSignal(str)

    def __init__(self, lat, lon, email, parent=None):
        super().__init__(parent)
        self._lat   = lat
        self._lon   = lon
        self._email = email

    def run(self):
        try:
            headers = {
                "User-Agent": f"CarrotPi/1.0 ({self._email})",
                "Accept":     "application/geo+json",
            }

            # Step 1: resolve grid point → forecast URL
            points_url = f"https://api.weather.gov/points/{self._lat},{self._lon}"
            req = urllib.request.Request(points_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            forecast_url = data["properties"]["forecast"]

            # Step 2: fetch forecast periods
            req2 = urllib.request.Request(forecast_url, headers=headers)
            with urllib.request.urlopen(req2, timeout=10) as resp2:
                data2 = json.loads(resp2.read().decode())
            periods = data2["properties"]["periods"]

            self.finished.emit(periods)

        except Exception as exc:
            self.error.emit(str(exc))


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

def _label(parent, x, y, w, h, text="", pt=14, bold=False,
           color="#e0e0e0", align=Qt.AlignLeft | Qt.AlignTop, wrap=False):
    lbl = QLabel(text, parent)
    lbl.setGeometry(x, y, w, h)
    lbl.setAlignment(align)
    lbl.setWordWrap(wrap)
    lbl.setStyleSheet(f"color: {color}; background: transparent;")
    lbl.setFont(QFont("Helvetica Neue", pt, QFont.Bold if bold else QFont.Normal))
    return lbl


# ---------------------------------------------------------------------------
# Period card — one column for each forecast period
# ---------------------------------------------------------------------------

_CARD_W    = WEATHER_W // _NUM_PERIODS   # ≈ 229 px
_CARD_PAD  = 12
_CARD_INNER = _CARD_W - _CARD_PAD * 2


class _PeriodCard:
    """Owns the four QLabels that make up one forecast period column."""

    def __init__(self, parent, col_index):
        x = col_index * _CARD_W

        # Thin separator line between cards (skip leftmost)
        if col_index > 0:
            sep = QWidget(parent)
            sep.setGeometry(x, 170, 1, WEATHER_H - 200)
            sep.setStyleSheet("background: #2a2a3e;")

        ix = x + _CARD_PAD

        self.name_lbl  = _label(parent, ix, 170, _CARD_INNER, 34,
                                pt=13, bold=True, color="#aaaaaa",
                                align=Qt.AlignHCenter | Qt.AlignVCenter)

        self.temp_lbl  = _label(parent, ix, 210, _CARD_INNER, 90,
                                pt=46, bold=True, color="#ffffff",
                                align=Qt.AlignHCenter | Qt.AlignVCenter)

        self.cond_lbl  = _label(parent, ix, 306, _CARD_INNER, 210,
                                pt=13, color="#cccccc",
                                align=Qt.AlignHCenter | Qt.AlignTop,
                                wrap=True)

        self.wind_lbl  = _label(parent, ix, 516, _CARD_INNER, 50,
                                pt=11, color="#888888",
                                align=Qt.AlignHCenter | Qt.AlignVCenter)

    def populate(self, period):
        unit = period.get("temperatureUnit", "F")
        self.name_lbl.setText(period.get("name", ""))
        self.temp_lbl.setText(f"{period.get('temperature', '--')}°{unit}")
        self.cond_lbl.setText(period.get("shortForecast", ""))
        speed = period.get("windSpeed", "")
        dirn  = period.get("windDirection", "")
        self.wind_lbl.setText(f"Wind {dirn} {speed}".strip())

    def show(self):
        for lbl in (self.name_lbl, self.temp_lbl, self.cond_lbl, self.wind_lbl):
            lbl.show()

    def hide(self):
        for lbl in (self.name_lbl, self.temp_lbl, self.cond_lbl, self.wind_lbl):
            lbl.hide()


# ---------------------------------------------------------------------------
# WeatherPage
# ---------------------------------------------------------------------------

class WeatherPage:
    """
    Owns a QWidget that displays NWS forecast data.
    Exposes show_page() / hide_page() matching the Maps/Spotify interface.
    """

    def __init__(self, parent=None):
        lat, lon, email = _read_weather_config()
        self._lat   = lat
        self._lon   = lon
        self._email = email
        self._fetcher = None          # holds active QThread; prevents GC while running

        # Root widget — replaces center_panel only; right_buttons stays visible
        self._widget = QWidget(parent)
        self._widget.setGeometry(WEATHER_X, WEATHER_Y, WEATHER_W, WEATHER_H)
        self._widget.setStyleSheet("background: #0a0a14;")

        # Header row — city/state label (populated from first period name fallback)
        self._header = _label(
            self._widget, 0, 20, WEATHER_W, 60,
            text="Weather",
            pt=28, bold=True, color="#ffffff",
            align=Qt.AlignHCenter | Qt.AlignVCenter
        )

        self._updated = _label(
            self._widget, 0, 80, WEATHER_W, 28,
            pt=12, color="#666666",
            align=Qt.AlignHCenter | Qt.AlignVCenter
        )

        # Divider
        div = QWidget(self._widget)
        div.setGeometry(20, 148, WEATHER_W - 40, 1)
        div.setStyleSheet("background: #2a2a3e;")

        # Status / error label (full widget, shown while loading or on error)
        self._status = _label(
            self._widget, 0, 0, WEATHER_W, WEATHER_H,
            text="Loading weather…",
            pt=22, color="#666666",
            align=Qt.AlignCenter
        )

        # Five period cards — hidden until data arrives
        self._cards = [_PeriodCard(self._widget, i) for i in range(_NUM_PERIODS)]
        for card in self._cards:
            card.hide()

        self._widget.hide()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show_page(self):
        self._set_loading()
        self._widget.show()
        self._widget.raise_()
        self._start_fetch()

    def hide_page(self):
        self._widget.hide()

    def update_location(self, lat, lon):
        """Update the lat/lon used for the next fetch (called by GPS)."""
        self._lat = lat
        self._lon = lon

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _set_loading(self):
        self._status.setText("Loading weather…")
        self._status.show()
        self._updated.setText("")
        for card in self._cards:
            card.hide()

    def _start_fetch(self):
        # Let any previous thread finish silently; its signals are still
        # connected and will harmlessly update hidden-then-shown labels.
        self._fetcher = WeatherFetcher(self._lat, self._lon, self._email)
        self._fetcher.finished.connect(self._on_data)
        self._fetcher.error.connect(self._on_error)
        self._fetcher.start()
        print(f"[weather] fetching  lat={self._lat}  lon={self._lon}")

    def _on_data(self, periods):
        print(f"[weather] received {len(periods)} period(s)")
        self._status.hide()

        for i, card in enumerate(self._cards):
            if i < len(periods):
                card.populate(periods[i])
                card.show()
            else:
                card.hide()

        # Show the name of the first period's city via the header
        # (NWS doesn't return city in the forecast — use period[0].name as subtitle)
        if periods:
            first_name = periods[0].get("name", "")
            self._header.setText("Weather")
            self._updated.setText(f"Starting {first_name.lower()}")

    def _on_error(self, msg):
        print(f"[weather] error: {msg}")
        for card in self._cards:
            card.hide()
        self._status.setText(f"Weather unavailable\n\n{msg}")
        self._status.show()
