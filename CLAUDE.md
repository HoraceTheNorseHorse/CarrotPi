# CarrotPi — VW Rabbit Carputer
## Claude Code Project Spec

This is an in-car computer frontend for a VW Rabbit, running on a
Raspberry Pi 5 (8GB) with a Waveshare 9.3" capacitive touchscreen.
Always read this file fully before writing any code.

---

## Hardware

- **Computer:** Raspberry Pi 5 8GB, 2.4GHz Quad-core Cortex-A76
- **Display:** Waveshare 9.3" capacitive touch, 1600×600 resolution
- **Relays:** 2× 4-channel relay HATs (I2C, on GPIO) + 8-channel 5V relay module = 16 relays total
- **Haptic:** Vibration motor (5V, all button presses trigger it)
- **GPS:** GPS module (model TBD)
- **Temp sensor:** Bojack temperature sensor (model TBD)
- **Audio:** HiFiBerry DAC HAT (exact model TBD — dig out of closet)
  - ALSA device name will be snd_rpi_hifiberry_dac or similar
  - Spotify playback via librespot (Spotify Connect daemon)
- **Power:** 41A 12V power supply

---

## Framework

- **Language:** Python 3
- **GUI:** PyQt5 (NOT Tkinter, NOT Kivy)
- **Maps/Spotify:** QWebEngineView (embedded browser)
- **Relay control:** smbus2 (I2C)
- **Dev platform:** macOS (mirror of Pi filesystem structure)
- **Run command (Mac):** `/opt/homebrew/bin/python3.11 main.py`
- **Run command (Pi):** `python3 main.py`

---

## Screen Layout

Total resolution: **1600×600**. Three fixed panels, no scrolling.

| Panel | File | Size | Position |
|---|---|---|---|
| Left switches | left_switches.png | 327×600 | x=0, y=0 |
| Center panel | center_panel.png | 1147×600 | x=328, y=0 |
| Right buttons | right_buttons.png | 124×600 | x=1476, y=0 |

Assets path (Pi): `/home/scottconnors/VW/assets/`
Assets path (dev): `./assets/`

---

## State Machine

All UI state is managed through a central state dict. Default state on launch:

```
mode        = light
defrost     = off
hazards     = off
home        = on
fan         = 0
floor       = on
temp        = cold
hvacdef     = off
maps        = off
spotify     = off
```

---

## Relay Mapping (I2C via smbus2)

| Relay | Function |
|---|---|
| 1 | Defrost |
| 2 | Hazards |
| 3 | Fan speed 1 |
| 4 | Fan speed 2 |
| 5 | Fan speed 3 |
| 6 | Temp (TBD) |
| 7 | HVAC defrost (TBD) |
| 8 | Floor (TBD) |
| 9–16 | Available — power windows, future use |

---

## HVAC Image Logic

| temp  | floor | hvacdef | Image |
|---|---|---|---|
| cold | on  | off | center_panel.png (no overlay) |
| cold | off | on  | hvac_2.png |
| cold | on  | on  | hvac_3.png |
| cold | off | off | hvac_4.png |
| hot  | off | on  | hvac_5.png |
| hot  | on  | on  | hvac_6.png |
| hot  | off | off | hvac_7.png |
| hot  | on  | off | hvac_8.png |

---

## Button Hit Zones (exact pixel coordinates, top-left origin)

### Left panel buttons
| Button | x1 | y1 | x2 | y2 |
|---|---|---|---|---|
| gti (exit app) | 88 | 70 | 240 | 160 |
| defrost_switch | 88 | 193 | 240 | 280 |
| hazards_switch | 88 | 317 | 240 | 402 |
| home_switch | 88 | 437 | 240 | 525 |

### Center panel buttons
| Button | x1 | y1 | x2 | y2 |
|---|---|---|---|---|
| fan_switch | 372 | 452 | 492 | 567 |
| volume | 384 | 88 | 536 | 250 |
| tuner | 1260 | 88 | 1413 | 250 |
| preset_1 | 620 | 210 | 702 | 260 |
| preset_2 | 730 | 210 | 820 | 260 |
| preset_3 | 855 | 210 | 941 | 260 |
| preset_4 | 972 | 210 | 1062 | 260 |
| preset_5 | 1086 | 210 | 1175 | 260 |
| floor_left | 562 | 375 | 703 | 440 |
| floor_right | 873 | 375 | 960 | 440 |
| def_left | 1021 | 375 | 1121 | 440 |
| def_right | 1300 | 375 | 1420 | 440 |
| temp_left | 562 | 488 | 703 | 562 |
| temp_right | 1300 | 488 | 1420 | 562 |

### Right panel buttons
| Button | x1 | y1 | x2 | y2 | Function |
|---|---|---|---|---|---|
| right_button_1 | 1476 | 0 | 1600 | 123 | WiFi settings |
| right_button_2 | 1476 | 123 | 1600 | 242 | Launch Google Maps |
| right_button_3 | 1476 | 242 | 1600 | 362 | Launch Spotify |
| right_button_4 | 1476 | 362 | 1600 | 480 | CarPlay / Android Auto |
| right_button_5 | 1476 | 480 | 1600 | 600 | Toggle weather / clock |

---

## Overlay Image Positions

| Image | Size | Position | Condition |
|---|---|---|---|
| defrost_on.png | 327×123 | x=0, y=187 | defrost=on |
| hazards_on.png | 327×122 | x=0, y=311 | hazards=on |
| hazards_flash.png | 327×122 | x=0, y=311 | hazards=on (alternates 0.5s) |
| home_off.png | 327×167 | x=0, y=433 | home=off |
| fan_1.png | 218×260 | x=332, y=340 | fan=1 |
| fan_2.png | 218×260 | x=332, y=340 | fan=2 |
| fan_3.png | 218×260 | x=332, y=340 | fan=3 |
| hvac_N.png | varies | x=554, y=330 | see HVAC table |

---

## Page Architecture

### Full-page takeover (Maps, Spotify)
- Hides center_panel AND right_buttons
- Shows home_off.png over left panel
- Disables all center/right buttons
- Sets home=off
- home_switch restores everything
- QWebEngineView fills x=328–1600, full 600px height

### Partial takeover (Weather)
- Hides center_panel ONLY
- right_buttons stays visible
- home_off.png NOT shown
- Buttons NOT disabled
- home=on unchanged
- right_button_5 toggles it on/off
- WeatherPage geometry: x=328, y=0, w=1147, h=600

### _press_home ordering (CRITICAL)
Weather check runs BEFORE the `home == "on"` guard in `_press_home`.
Weather leaves home="on", so without this ordering, pressing home
while weather is visible would silently no-op instead of closing it.

### Edge case: Maps/Spotify → Weather
Pressing right_button_5 while Maps or Spotify is open calls
`_press_home()` first to restore right_buttons and re-enable buttons,
then shows weather in center_panel. Clean transition, no orphaned state.

---

## Implementation Notes

### Button dispatch
Buttons wired via dict mapping name strings to handler methods.
Adding a button = one new dict entry, no if/elif chains.

### HVAC_TABLE
```python
HVAC_TABLE = {
    ('cold', 'on',  'off'): None,
    ('cold', 'off', 'on'):  'hvac_2',
    ...
}
```
Tuple-keyed dict, O(1) lookup, single source of truth.

### HVAC_OVERLAY_KEYS
Built at module load by filtering OVERLAYS for `hvac_` prefixes.
Adding a new hvac image = add to OVERLAYS only, no other changes.

### Paired HVAC buttons
floor_left/floor_right, def_left/def_right, temp_left/temp_right
all point to the same handler. Both sides toggle same state variable.

### Clock
QTimer fires every 500ms. Colon visible on even ticks, hidden on odd.
QLabel in right_button_5 zone. Clock does not block touch events.

### VolumeOverlay (in main.py)
Arc drawn with QPainter. `_ARC_START = 225 * 16` (7-o'clock).
`_ARC_SPAN = -270 * 16` (clockwise 270° to 5-o'clock).
Foreground arc span proportional to volume: at 100% equals full bg arc.

Drag-to-angle: `atan2(-dy, dx)` → math-convention angle → clockwise
offset from arc start: `(225 - angle_deg) % 360`. Offsets >270° clamp
to nearest endpoint (315°+ → 0, 270°–315° → 100).

`_snap()` rounds to nearest multiple of 5: `round(vol / 5) * 5`.
Subprocess only fires when snapped value changes — not every drag tick.

`_set_system_volume` spawns daemon thread (same pattern as haptic.py):
- macOS: `osascript -e "set volume output volume {vol}"`
- Pi/Linux: `amixer sset Master {vol}%`
Detects platform with `platform.system()`.

Z-order: VolumeOverlay constructed last in `_init_ui` + `raise_()` in
`show_overlay()` — always above transparent QPushButton layer.

Toggle: `show_overlay()` checks `isVisible()` first — second tap hides
immediately. 3-second QTimer handles "walked away" case.

### WeatherFetcher(QThread)
Two-step NWS fetch off main thread. Step 1: `/points/{lat},{lon}`
resolves grid-unique forecast URL. Step 2: fetches period list.
Results via pyqtSignal (Qt marshals to main thread automatically).
`self._fetcher` instance var keeps thread alive — local var would
allow GC to destroy C++ thread mid-run.

### Graceful hardware fallback
All relay/haptic/GPIO calls wrapped in try/except. Silent fail on Mac.

---

## Maps Implementation

**Mode switching via config.ini:**
- `maps_mode = leaflet` (default) — loads local assets/maps.html
  via QUrl.fromLocalFile. Works on Mac. Uses Leaflet + OSRM routing.
- `maps_mode = google` — loads https://maps.google.com with Chrome UA.
  Works on Pi. Crashes on macOS (Chromium JIT signing restriction).

**Leaflet map (assets/maps.html):**
- Leaflet 1.9.4 + Leaflet Routing Machine 3.2.12 from CDN
- CartoDB Voyager tiles (no Referer header required — OSM tiles block file:// URLs)
- OSRM public routing API for turn-by-turn
- Nominatim geocoding for address → coordinates
- circleMarker for GPS position dot
- `updatePosition(lat, lng)` global function for GPS injection
- Default center: lat=40.0639, lng=-80.7209

**`update_location(lat, lng)`** — calls runJavaScript in leaflet mode,
no-op in google mode.

---

## Spotify Implementation

**Mode switching via config.ini:**
- `spotify_mode = placeholder` (default) — dark QWidget with
  "Connect HiFiBerry DAC to enable audio" message. Works on Mac.
- `spotify_mode = web` — loads https://open.spotify.com with Chrome UA.
  Works on Pi. Same JIT issue as Google Maps on Mac.

**Pi audio:** librespot (Spotify Connect daemon) handles all audio
routing to HiFiBerry DAC. CarrotPi UI just shows the web player.
See PI_DEPLOY.md for librespot setup.

---

## Weather Implementation (pages/weather.py)

**API:** NWS (National Weather Service) — free, no API key required.
**Geometry:** x=328, y=0, w=1147, h=600 (center panel only).

**WeatherFetcher(QThread):** Two-step fetch off main thread.
Step 1: `https://api.weather.gov/points/{lat},{lon}` → forecast URL.
Step 2: forecast URL → period list. Results via pyqtSignal.

**_PeriodCard:** Owns 4 QLabels (name, temp, forecast, wind).
Cards shown/hidden as unit. Dark styling, large touch-friendly fonts.

**show_page():** Always triggers fresh fetch. Loading state displays
immediately while thread runs. Error message shown on API failure.

**update_location(lat, lng):** Accepts GPS coordinates for future
live weather based on actual car position.

---

## Planned but Not Yet Implemented

- Light/dark mode (alternate image set, headlight relay trigger)
- Power windows interface (overhead car view, 4 window controls)
- GPS live feed → maps + weather update_location()
- Bojack temp sensor → right_button_5 display alongside clock
- Volume control UI (volume button on center panel)
- WiFi settings page (right_button_1)
- CarPlay / Android Auto (right_button_4) — OpenAuto abandoned, TBD
- OBD2 integration (pending Rabbit year confirmation)
- Animated splash screen (.mp4/.mov, fullscreen on boot)
- Hardware: relay I2C addresses (verify with i2cdetect on Pi)
- Hardware: haptic GPIO pin (verify wiring)
- Hardware: GPS device path (/dev/ttyACM0 or /dev/ttyUSB0)

---

## Project File Structure

```
carrotpi/
  CLAUDE.md          ← this file
  PI_DEPLOY.md       ← Pi deployment checklist
  config.ini.example ← template (copy to config.ini, gitignored)
  main.py            ← entry point, window, state machine
  assets/
    *.png            ← all panel and overlay images
    maps.html        ← Leaflet map with routing
  pages/
    maps.py          ← Google Maps / Leaflet page
    spotify.py       ← Spotify web player page
    weather.py       ← NWS weather page
  hardware/
    relays.py        ← smbus2 I2C relay control (16 relays)
    haptic.py        ← vibration motor GPIO control
    gps.py           ← GPS module (not yet built)
    temp.py          ← Bojack temp sensor (not yet built)
```

---

## Mac vs Pi Quick Reference

| Item | Mac | Pi |
|---|---|---|
| Python | `/opt/homebrew/bin/python3.11` | `python3` |
| maps_mode | `leaflet` | `google` |
| spotify_mode | `placeholder` | `web` |
| Hardware calls | silently skipped | active |
| Audio | none | HiFiBerry via librespot |
| GPS | hardcoded default coords | gpsd live feed |
| JIT signing | problem (macOS SIP) | not an issue |
