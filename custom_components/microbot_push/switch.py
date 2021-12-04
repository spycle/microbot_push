"""Support for MicroBot Push."""

from . import microbot
from .microbot import MicroBotPush
import voluptuous as vol
import logging

from homeassistant.components.switch import PLATFORM_SCHEMA, SwitchEntity
from homeassistant.const import CONF_NAME
import homeassistant.helpers.config_validation as cv
import re

_LOGGER = logging.getLogger(__name__)

CONF_BDADDR = "bdaddr"
DEFAULT_NAME = "MicroBotPush"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Required(CONF_BDADDR): cv.string,
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None) -> None:
    """Perform the setup for MicroBot devices."""
    name = config.get(CONF_NAME)
    bdaddr = config.get(CONF_BDADDR)
    conf_dir = hass.config.path()
    conf = conf_dir+"/microbot-"+re.sub('[^a-f0-9]', '', bdaddr.lower())+".conf"
    socket_path = conf_dir+"/microbot-"+re.sub('[^a-f0-9]', '', bdaddr.lower())
    device = MicroBotPush(bdaddr, conf, socket_path, newproto=True, is_server=False)
    add_entities([MicroBotPushEntity(bdaddr, name, conf, socket_path, device)], True)


class MicroBotPushEntity(SwitchEntity):
    """Representation of a MicroBot."""

    def __init__(self, bdaddr, name, conf, socket_path, device) -> None:
        """Initialize the MicroBot."""

        self._device = device
        self._conf = conf
        self._socket_path = socket_path
        self._bdaddr = bdaddr
        self._name = name
        self._is_on = False

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return self._bdaddr.replace(":", "")

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return True
#        return self._device.available()

    @property
    def name(self) -> str:
        """Return the name of the switch."""
        return self._name

    @property
    def is_on(self) -> bool:
        """Return true if it is on."""
        return self._is_on

    @property
    def assumed_state(self) -> bool:
        return False

    def turn_on(self) -> None:
        """Turn the switch on."""

        self._device.connect()
        self._device.push('noparams')
        self._device.disconnect()
        self._is_on = True
        return True

    def turn_off(self) -> None:
        """Turn the switch off."""
        self._device.connect()
        self._device.push('noparams')
        self._device.disconnect()
        self._is_on = False
        return True
