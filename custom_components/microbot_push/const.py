"""Constants for integration_blueprint."""
# Base component constants
NAME = "MicroBot Push"
DOMAIN = "microbot_push"
DOMAIN_DATA = f"{DOMAIN}_data"
VERSION = "2022.7.2"
ATTRIBUTION = "Data provided by http://jsonplaceholder.typicode.com/"
ISSUE_URL = "https://github.com/spycle/microbot_push/issues"

# Icons
ICON = "mdi:toggle-switch-variant"

# Device classes
BINARY_SENSOR_DEVICE_CLASS = "connectivity"

# Platforms
BINARY_SENSOR = "binary_sensor"
SENSOR = "sensor"
SWITCH = "switch"
PLATFORMS = [SWITCH]


# Configuration and options
CONF_ENABLED = "enabled"
CONF_NAME = "name"
CONF_PASSWORD = "password"
CONF_BDADDR = "bdaddr"
DEFAULT_TIMEOUT = 10

# Defaults
DEFAULT_NAME = "MicroBotPush"


STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""
