"""
pages/maps.py — Map page with two modes selected by config.ini [maps] maps_mode.

  leaflet (default) — loads assets/maps.html (Leaflet + OpenStreetMap).
                      Works on macOS and Pi. No API key required.

  google            — loads https://maps.google.com with a Chrome user agent.
                      Works on Pi. Crashes on macOS due to missing
                      com.apple.security.cs.allow-jit entitlement on the
                      pip-installed QtWebEngineProcess subprocess (SIGABRT).

Geometry: x=328, y=0, w=1272, h=600.
show_page() / hide_page() interface is identical in both modes.

IMPORTANT: QtWebEngineWidgets must be imported before QApplication is
instantiated. This module is imported at the top of main.py to satisfy
that requirement on both macOS and Pi.
"""

import os
import configparser

from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEnginePage, QWebEngineSettings
from PyQt5.QtCore import QUrl

MAPS_X = 328
MAPS_Y = 0
MAPS_W = 1272
MAPS_H = 600

_HERE      = os.path.dirname(__file__)
_HTML_PATH = os.path.join(_HERE, "..", "assets", "maps.html")
_CFG_PATH  = os.path.join(_HERE, "..", "config.ini")

_GOOGLE_URL = "https://maps.google.com"
_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux aarch64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def _read_maps_mode():
    cfg = configparser.ConfigParser()
    cfg.read(_CFG_PATH)
    return cfg.get("maps", "maps_mode", fallback="leaflet").strip().lower()


class MapsPage(QWebEngineView):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setGeometry(MAPS_X, MAPS_Y, MAPS_W, MAPS_H)

        self._mode = _read_maps_mode()
        print(f"[maps] mode: {self._mode}")

        if self._mode == "google":
            profile = QWebEngineProfile(self)
            profile.setHttpUserAgent(_USER_AGENT)
            self.setPage(QWebEnginePage(profile, self))

        # Allow file:// pages to make cross-origin fetch requests.
        # Required for Leaflet mode: maps.html is loaded from file://, but
        # needs to reach Nominatim (geocoding) and OSRM (routing) over HTTPS.
        # Chromium blocks these by default when the origin is file://.
        self.settings().setAttribute(
            QWebEngineSettings.LocalContentCanAccessRemoteUrls, True
        )

        self._loaded = False
        self.hide()

    def show_page(self):
        if not self._loaded:
            if self._mode == "google":
                self.load(QUrl(_GOOGLE_URL))
            else:
                self.load(QUrl.fromLocalFile(os.path.abspath(_HTML_PATH)))
            self._loaded = True
        self.show()
        self.raise_()

    def hide_page(self):
        self.hide()

    def update_location(self, lat, lng):
        """Push a GPS position update into the Leaflet map (leaflet mode only)."""
        self.page().runJavaScript(f"updatePosition({lat}, {lng})")
