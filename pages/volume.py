"""
pages/volume.py — Circular arc volume control overlay.

A 280×280 QWidget drawn with QPainter that floats above the volume knob area.
Shows a 270° arc (gray background + colored foreground) with the current
volume percentage centered inside it.

Interaction:
  - Drag anywhere on the widget: angle from center maps to volume 0–100
  - Volume snaps to nearest 5
  - Auto-dismisses after 3 s of inactivity (QTimer)
  - Toggle: show_overlay() shows on first call, hides if already visible

System volume:
  - macOS: osascript
  - Linux: amixer sset Master
  Subprocess calls run on daemon threads — never block the UI.
"""

import math
import platform
import subprocess
import threading

from PyQt5.QtWidgets import QWidget, QLabel
from PyQt5.QtGui import QPainter, QPen, QColor, QFont
from PyQt5.QtCore import Qt, QTimer, QRect

# ---------------------------------------------------------------------------
# Geometry — centered on the volume knob hit zone (x=384–536, y=88–250)
# ---------------------------------------------------------------------------
_KNOB_CX = (384 + 536) // 2   # 460
_KNOB_CY = ( 88 + 250) // 2   # 169

OVERLAY_W = 280
OVERLAY_H = 280
OVERLAY_X = _KNOB_CX - OVERLAY_W // 2   # 320
OVERLAY_Y = _KNOB_CY - OVERLAY_H // 2   # 29

# Arc geometry
_ARC_START   =  225 * 16   # Qt CCW degrees × 16 — 7-o'clock position
_ARC_SPAN    = -270 * 16   # sweep CW 270°
_STROKE      = 18           # arc pen width (px)
_ARC_MARGIN  = _STROKE // 2 + 6

# Colors
_COLOR_BG    = QColor( 55,  55,  65)     # gray track
_COLOR_FG    = QColor(255, 160,   0)     # amber foreground arc
_COLOR_TEXT  = QColor(255, 255, 255)
_COLOR_PANEL = QColor( 14,  14,  30, 210)  # semi-transparent dark bg

_DISMISS_MS  = 3000   # auto-dismiss after 3 s inactivity
_VOL_STEP    = 5      # snap to multiples of 5


# ---------------------------------------------------------------------------
# Platform volume helpers
# ---------------------------------------------------------------------------

def _get_system_volume() -> int:
    """Return current output volume 0–100, or 50 on failure."""
    try:
        if platform.system() == "Darwin":
            r = subprocess.run(
                ["osascript", "-e", "get output volume of (get volume settings)"],
                capture_output=True, text=True, timeout=2
            )
            return max(0, min(100, int(r.stdout.strip())))
        else:
            import re
            r = subprocess.run(
                ["amixer", "sget", "Master"],
                capture_output=True, text=True, timeout=2
            )
            m = re.search(r'\[(\d+)%\]', r.stdout)
            if m:
                return int(m.group(1))
    except Exception:
        pass
    return 50


def _set_system_volume(vol: int) -> None:
    """Set output volume on a daemon thread — non-blocking."""
    def _worker():
        try:
            if platform.system() == "Darwin":
                subprocess.run(
                    ["osascript", "-e", f"set volume output volume {vol}"],
                    timeout=2
                )
            else:
                subprocess.run(
                    ["amixer", "sset", "Master", f"{vol}%"],
                    timeout=2
                )
        except Exception:
            pass
    threading.Thread(target=_worker, daemon=True).start()


# ---------------------------------------------------------------------------
# VolumeOverlay
# ---------------------------------------------------------------------------

class VolumeOverlay(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setGeometry(OVERLAY_X, OVERLAY_Y, OVERLAY_W, OVERLAY_H)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._volume  = 50
        self._dragging = False

        # Auto-dismiss timer — single-shot, restarts on each interaction
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(_DISMISS_MS)
        self._timer.timeout.connect(self.hide)

        self.hide()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show_overlay(self):
        """Toggle: show and sync volume on first call; hide if already visible."""
        if self.isVisible():
            self.hide()
            self._timer.stop()
            return

        self._volume = _snap(self._get_current_volume())
        self.raise_()
        self.show()
        self.update()
        self._reset_timer()

    def _get_current_volume(self) -> int:
        return _get_system_volume()

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2

        # Semi-transparent dark circular background
        painter.setPen(Qt.NoPen)
        painter.setBrush(_COLOR_PANEL)
        painter.drawEllipse(QRect(4, 4, w - 8, h - 8))

        painter.setBrush(Qt.NoBrush)
        arc_rect = QRect(_ARC_MARGIN, _ARC_MARGIN,
                         w - _ARC_MARGIN * 2,
                         h - _ARC_MARGIN * 2)

        # Background (gray) track arc
        pen_bg = QPen(_COLOR_BG, _STROKE, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen_bg)
        painter.drawArc(arc_rect, _ARC_START, _ARC_SPAN)

        # Foreground (amber) volume arc
        span = int(self._volume / 100.0 * 270 * 16)
        if span > 0:
            pen_fg = QPen(_COLOR_FG, _STROKE, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen_fg)
            painter.drawArc(arc_rect, _ARC_START, -span)

        # Volume percentage text
        painter.setPen(_COLOR_TEXT)
        painter.setFont(QFont("Helvetica Neue", 38, QFont.Bold))
        painter.drawText(QRect(0, -10, w, h), Qt.AlignCenter, f"{self._volume}")

        # Unit label below number
        painter.setPen(QColor(180, 180, 180))
        painter.setFont(QFont("Helvetica Neue", 13))
        painter.drawText(QRect(0, 30, w, h), Qt.AlignCenter, "vol")

        painter.end()

    # ------------------------------------------------------------------
    # Mouse interaction
    # ------------------------------------------------------------------

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._reset_timer()
            self._update_from_pos(event.pos())

    def mouseMoveEvent(self, event):
        if self._dragging:
            self._reset_timer()
            self._update_from_pos(event.pos())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False

    def _update_from_pos(self, pos):
        cx, cy = self.width() // 2, self.height() // 2
        dx = pos.x() - cx
        dy = pos.y() - cy    # screen: positive = downward

        # atan2 in math convention: negate dy to convert screen→math y-axis
        angle_deg = math.degrees(math.atan2(-dy, dx))
        if angle_deg < 0:
            angle_deg += 360   # 0–360 CCW from 3 o'clock

        # Arc starts at 225° CCW from 3 o'clock and sweeps CW 270°.
        # CW offset from start = (225 - angle) mod 360
        offset = (225 - angle_deg) % 360

        # Points outside the 270° arc clamp to the nearest endpoint
        if offset > 270:
            offset = 0 if offset > 315 else 270

        raw    = int(offset / 270 * 100)
        volume = _snap(max(0, min(100, raw)))

        if volume != self._volume:
            self._volume = volume
            self.update()
            _set_system_volume(volume)

    # ------------------------------------------------------------------
    # Timer
    # ------------------------------------------------------------------

    def _reset_timer(self):
        self._timer.stop()
        self._timer.start()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _snap(vol: int) -> int:
    """Round volume to nearest multiple of _VOL_STEP."""
    return round(vol / _VOL_STEP) * _VOL_STEP
