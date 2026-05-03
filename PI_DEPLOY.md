# CarrotPi — Raspberry Pi Deployment Checklist

This document covers everything needed to move from Mac development
to a running Pi installation. Work through it top to bottom.

---

## 1. Pi OS Setup

- Flash Raspberry Pi OS (64-bit, Bookworm) to SD card
- Boot, complete initial setup, connect to WiFi
- Enable SSH: `sudo raspi-config` → Interface Options → SSH → Enable
- Set hostname to `carrotpi` (optional but useful)
- Run: `sudo apt update && sudo apt upgrade -y`

---

## 2. Install Python Dependencies

```bash
sudo apt install -y python3-pip python3-pyqt5 python3-pyqt5.qtwebengine \
  python3-pyqt5.qtmultimedia python3-smbus i2c-tools git
pip3 install python-obd gps folium requests
```

> Note: On Pi, use system PyQt5 (apt) not pip — the apt version is
> compiled with proper hardware acceleration flags.

---

## 3. Clone / Copy Project

```bash
git clone <repo-url> ~/carrotpi
# OR copy from Mac via scp:
# scp -r ~/Developer/carrotpi pi@carrotpi.local:~/carrotpi
```

---

## 4. HiFiBerry DAC Setup

Identify your exact HiFiBerry model, then:

```bash
sudo nano /boot/firmware/config.txt
```

Add the correct overlay for your board (comment out dtparam=audio=on):
```
# dtparam=audio=on          ← comment this out
dtoverlay=hifiberry-dac     ← for DAC / DAC+
# dtoverlay=hifiberry-dacplus  ← for DAC+ Standard/Pro
# dtoverlay=hifiberry-dacplusadcpro  ← for DAC+ ADC Pro
```

Reboot, then verify:
```bash
aplay -l   # should show sndrpihifiberry
```

Update `config.ini` with the correct ALSA device name from aplay output.

---

## 5. librespot (Spotify Connect)

Requires Spotify Premium.

```bash
# Install librespot
curl -sL https://dtcooper.github.io/raspotify/install.sh | sh

# Configure it
sudo nano /etc/raspotify/conf
```

Set these values in conf:
```
LIBRESPOT_NAME="CarrotPi"
LIBRESPOT_BACKEND="alsa"
LIBRESPOT_DEVICE="hw:0"          ← match aplay -l output
LIBRESPOT_BITRATE="320"
LIBRESPOT_DEVICE_TYPE="speaker"
```

```bash
sudo systemctl enable raspotify
sudo systemctl start raspotify
```

Test: Open Spotify on Scott's phone → devices → "CarrotPi" should appear.

---

## 6. GPS Setup

```bash
sudo apt install -y gpsd gpsd-clients
sudo nano /etc/default/gpsd
```

Set:
```
DEVICES="/dev/ttyACM0"     ← or /dev/ttyUSB0 depending on GPS module
GPSD_OPTIONS="-n"
START_DAEMON="true"
```

```bash
sudo systemctl enable gpsd
sudo systemctl start gpsd
cgps -s   # verify GPS is getting a fix (may need clear sky view)
```

---

## 7. I2C Setup (Relays + Temp Sensor)

```bash
sudo raspi-config  # → Interface Options → I2C → Enable
sudo reboot
i2cdetect -y 1    # verify relay boards are detected
```

Expected addresses:
- 4-channel relay HAT: typically 0x20
- Bojack temp sensor: varies by model (check datasheet)

Update `hardware/relays.py` with correct I2C addresses if different
from defaults.

---

## 8. config.ini (CRITICAL — create this file on the Pi)

Copy the example and edit:
```bash
cd ~/carrotpi
cp config.ini.example config.ini
nano config.ini
```

Change these values from Mac defaults to Pi values:

```ini
[maps]
maps_mode = google          # was: leaflet

[spotify]
spotify_mode = web          # was: placeholder

[audio]
alsa_device = hw:0          # match aplay -l output for HiFiBerry
hifiberry_model = dac       # dac / dacplus / dacplusadcpro

[hardware]
relay_hat_address = 0x20    # verify with i2cdetect
temp_sensor_pin = 4         # GPIO pin for Bojack sensor

[display]
screen_width = 1600
screen_height = 600
```

---

## 9. Run on Boot

```bash
sudo nano /etc/xdg/autostart/carrotpi.desktop
```

Add:
```
[Desktop Entry]
Type=Application
Name=CarrotPi
Exec=/usr/bin/python3 /home/pi/carrotpi/main.py
```

---

## 10. Run Command

```bash
cd ~/carrotpi && python3 main.py
```

> On Pi, use system `python3` (not Homebrew). The JIT signing issue
> is macOS-only — QtWebEngine runs normally on Pi Linux.

---

## Things Still TBD at Deployment Time

- [ ] HiFiBerry exact model → correct dtoverlay
- [ ] GPS module exact device path (`/dev/ttyACM0` vs `/dev/ttyUSB0`)
- [ ] Bojack temp sensor GPIO pin and protocol (1-wire vs I2C)
- [ ] I2C addresses for relay boards (verify with i2cdetect)
- [ ] Vibration motor GPIO pin
- [ ] OBD2 adapter (if year of Rabbit supports it)
- [ ] Splash screen video setup
- [ ] Light/dark mode assets (not yet created)
- [ ] 12V → 5V power wiring for Pi from car supply
- [ ] Waveshare display rotation config if needed

---

## Mac vs Pi Quick Reference

| Setting | Mac (dev) | Pi (production) |
|---|---|---|
| Python | `/opt/homebrew/bin/python3.11` | `python3` |
| maps_mode | `leaflet` | `google` |
| spotify_mode | `placeholder` | `web` |
| Hardware calls | silently skipped | active |
| Audio | none | HiFiBerry DAC |
| GPS | hardcoded default | gpsd live feed |
