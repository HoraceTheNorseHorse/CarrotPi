# CarrotPi

An in-car computer for a 1980 VW Rabbit. Touchscreen dashboard, HVAC controls, maps, music, and weather — built on a Raspberry Pi 5.

## What it does

CarrotPi replaces the original Rabbit's center stack with a 9.3" touchscreen running a custom Python/PyQt5 interface. Tap controls drive the heater fan, defrost, hazards, and floor vents through a bank of relays. The right side of the screen swaps between Google Maps, Spotify (via librespot), and a weather page that pulls live forecasts from the National Weather Service.

## Hardware

- **Raspberry Pi 5** (8GB) — quad-core Cortex-A76
- **Waveshare 9.3" capacitive touchscreen** — 1600×600
- **HiFiBerry DAC HAT** — audio out to the Rabbit's speakers
- **2× 4-channel I2C relay HATs + 1× 8-channel relay module** — 16 relays for HVAC, hazards, defrost, future power windows
- **GPS module** — for live maps and weather location
- **Bojack temp sensor** — cabin temperature display
- **Vibration motor** — haptic feedback on every button press
- **41A 12V power supply** — wired into the Rabbit's electrical system

## Software

```
main.py            ← entry point, window, state machine, button dispatch
pages/
  maps.py          ← Google Maps (Pi) / Leaflet (Mac dev)
  spotify.py       ← Spotify web player (Pi) / placeholder (Mac)
  weather.py       ← NWS forecast page
  volume.py        ← Draggable arc volume overlay
hardware/
  relays.py        ← I2C relay control via smbus2
  haptic.py        ← Vibration motor (silently no-op on Mac)
assets/            ← Panel and overlay PNGs
```

The app runs on both Mac (for development) and Pi (for production). Hardware calls fail silently on Mac so the UI can be iterated on without the car. Behavior switches between Mac and Pi via `config.ini`.

## Running it

**Mac (dev):**
```bash
/opt/homebrew/bin/python3.11 main.py
```

**Pi (production):**
```bash
python3 main.py
```

See [PI_DEPLOY.md](PI_DEPLOY.md) for the full Raspberry Pi setup checklist (HiFiBerry, librespot, GPS, I2C, autostart).

## Project documentation

- **[CLAUDE.md](CLAUDE.md)** — full project spec: hardware map, screen layout, state machine, relay assignments, button hit zones, implementation notes
- **[PI_DEPLOY.md](PI_DEPLOY.md)** — step-by-step Raspberry Pi deployment guide

## Status

Working: dashboard UI, HVAC overlay logic, maps, Spotify, weather, volume control.

In progress / TBD: GPS live feed wiring, temp sensor display, WiFi settings page, light/dark mode, power windows interface, OBD2 integration, Pi hardware deployment.
