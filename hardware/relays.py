"""
Relay control via smbus2 (I2C) for two 52Pi 4-channel relay boards.

Board 1 — I2C address 0x10 — relays 1–4
Board 2 — I2C address 0x11 — relays 5–8

Each board is controlled by writing a single state byte where each bit
corresponds to one relay channel (bit 0 = CH1 … bit 3 = CH4).
A 1 bit = relay ON; a 0 bit = relay OFF.

Relay map (from CLAUDE.md):
    1  Defrost
    2  Hazards
    3  Fan speed 1
    4  Fan speed 2
    5  Fan speed 3
    6  Temp (TBD)
    7  HVAC defrost (TBD)
    8  Floor (TBD)

Fails silently on platforms where smbus2 is unavailable (e.g. macOS dev).
"""

try:
    import smbus2
    _bus = smbus2.SMBus(1)
    _AVAILABLE = True
except Exception:
    _bus = None
    _AVAILABLE = False

# I2C addresses for the two relay boards
_BOARD_ADDR = {
    1: 0x10,   # relays 1-4
    2: 0x11,   # relays 5-8
}

# Current relay state bytes, one per board (bit per channel, starts all-off)
_state = {1: 0x00, 2: 0x00}


def _board_and_bit(relay: int) -> tuple[int, int]:
    """Return (board_number, bit_index) for relay 1–8."""
    if not 1 <= relay <= 8:
        raise ValueError(f"Relay number must be 1–8, got {relay}")
    board = 1 if relay <= 4 else 2
    bit   = (relay - 1) % 4
    return board, bit


def _flush(board: int) -> None:
    """Write the current state byte for a board to I2C."""
    if not _AVAILABLE:
        return
    try:
        _bus.write_byte(_BOARD_ADDR[board], _state[board])
    except Exception:
        pass


def relay_on(relay: int) -> None:
    """Energise a relay by number (1–8)."""
    board, bit = _board_and_bit(relay)
    _state[board] |= (1 << bit)
    _flush(board)


def relay_off(relay: int) -> None:
    """De-energise a relay by number (1–8)."""
    board, bit = _board_and_bit(relay)
    _state[board] &= ~(1 << bit)
    _flush(board)


def all_off() -> None:
    """De-energise all relays on both boards."""
    for board in _state:
        _state[board] = 0x00
        _flush(board)
