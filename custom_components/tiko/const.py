"""Constants for the Tiko integration."""

DOMAIN = "tiko"

# Supported heating modes
MODE_NORMAL = "on"
MODE_OFF = "off"
MODE_FROST = "frost"
MODE_ABSENCE = "absence"

# Mapping between Tiko and HA modes
HA_MODE_MAP = {
    MODE_NORMAL: "heat",
    MODE_OFF: "off",
    MODE_FROST: "eco",
    MODE_ABSENCE: "away",
}

TIKO_MODE_MAP = {v: k for k, v in HA_MODE_MAP.items()}
