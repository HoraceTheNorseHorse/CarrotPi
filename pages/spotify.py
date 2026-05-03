"""
pages/spotify.py — Spotify page with two modes selected by config.ini [spotify] spotify_mode.

  placeholder (default) — dark QWidget with centered status text.
                          Works everywhere, no audio hardware required.

  web                   — loads https://open.spotify.com with a Chrome desktop
                          user agent in a private QWebEngineProfile.
                          Requires Spotify Premium and Pi audio hardware (e.g. HiFiBerry DAC).
                          May exhibit the same macOS JIT/entitlement crash as Google Maps —
                          use placeholder mode for Mac development.

Geometry: x=328, y=0, w=1272, h=600.
show_page() / hide_page() interface is identical in both modes.

IMPORTANT: In web mode, QtWebEngineWidgets must be imported before QApplication
is instantiated. pages/maps.py already satisfies this requirement when imported
at the top of main.py — no separate early import needed here.
"""

import os
import configparser

from PyQt5.QtWidgets import QWidget, QLabel
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtCore import Qt

_HERE     = os.path.dirname(__file__)
_CFG_PATH = os.path.join(_HERE, "..", "config.ini")

SPOTIFY_X = 328
SPOTIFY_Y = 0
SPOTIFY_W = 1272
SPOTIFY_H = 600

_SPOTIFY_URL = "https://open.spotify.com"
_USER_AGENT  = (
    "Mozilla/5.0 (X11; Linux aarch64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
_PLACEHOLDER_TEXT = "Spotify\nConnect HiFiBerry DAC to enable audio"


def _read_spotify_mode():
    cfg = configparser.ConfigParser()
    cfg.read(_CFG_PATH)
    return cfg.get("spotify", "spotify_mode", fallback="placeholder").strip().lower()


def _build_placeholder(parent):
    """Return a dark QWidget with centered status text."""
    widget = QWidget(parent)
    widget.setGeometry(SPOTIFY_X, SPOTIFY_Y, SPOTIFY_W, SPOTIFY_H)
    widget.setStyleSheet("background: #0e0e1a;")

    label = QLabel(_PLACEHOLDER_TEXT, widget)
    label.setAlignment(Qt.AlignCenter)
    label.setGeometry(0, 0, SPOTIFY_W, SPOTIFY_H)
    label.setStyleSheet("color: #888; background: transparent;")
    font = QFont("Helvetica Neue", 24)
    label.setFont(font)

    return widget


def _build_web_view(parent):
    """Return a QWebEngineView loaded with open.spotify.com."""
    # Import here so the module is safe to import even if QtWebEngineWidgets
    # is unavailable; placeholder mode never touches this code path.
    from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEnginePage, QWebEngineSettings
    from PyQt5.QtCore import QUrl

    view = QWebEngineView(parent)
    view.setGeometry(SPOTIFY_X, SPOTIFY_Y, SPOTIFY_W, SPOTIFY_H)

    profile = QWebEngineProfile("spotify", view)
    profile.setHttpUserAgent(_USER_AGENT)

    page = QWebEnginePage(profile, view)
    view.setPage(page)

    view.settings().setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)

    view.load(QUrl(_SPOTIFY_URL))
    return view


class SpotifyPage:
    """
    Thin wrapper that owns either a placeholder QWidget or a QWebEngineView.
    Exposes show_page() / hide_page() regardless of mode.
    """

    def __init__(self, parent=None):
        self._mode = _read_spotify_mode()
        print(f"[spotify] mode: {self._mode}")

        if self._mode == "web":
            self._widget = _build_web_view(parent)
        else:
            self._widget = _build_placeholder(parent)

        self._widget.hide()

    def show_page(self):
        self._widget.show()
        self._widget.raise_()

    def hide_page(self):
        self._widget.hide()
