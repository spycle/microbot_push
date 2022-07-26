"""
Custom integration to integrate MicroBot with Home Assistant.

For more details about this integration, please refer to
https://github.com/spycle/microbot_push
"""
import asyncio
from datetime import timedelta
import logging
import re

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Config, HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.core import HomeAssistant, ServiceCall, callback

from .api import MicroBotApiClient

from .const import (
    CONF_BDADDR,
    CONF_NAME,
    DOMAIN,
    PLATFORMS,
    STARTUP_MESSAGE,
)

SCAN_INTERVAL = timedelta(minutes=10)

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup(hass: HomeAssistant, config: Config):
    """Set up this integration using YAML is not supported."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up this integration using UI."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})
        _LOGGER.debug(STARTUP_MESSAGE)

    bdaddr = entry.data.get(CONF_BDADDR)
    name = entry.data.get(CONF_NAME)
    conf_dir = hass.config.path()
    conf = conf_dir+"/.storage/microbot-"+re.sub('[^a-f0-9]', '', bdaddr.lower())+".conf"
    client = MicroBotApiClient(bdaddr, conf)
    coordinator = MicroBotDataUpdateCoordinator(hass, client=client)

    hass.data[DOMAIN][entry.entry_id] = coordinator

    for platform in PLATFORMS:
        coordinator.platforms.append(platform)
        hass.async_add_job(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )

    @callback
    async def generate_token(call: ServiceCall) -> None:
        _LOGGER.debug("Token service called")
        await coordinator.api.connect(init=True)

    @callback
    async def calibrate(call: ServiceCall) -> None:
        _LOGGER.debug("Calibrate service called")
        depth = call.data["depth"]
        duration = call.data["duration"]
        mode = call.data["mode"]
        await coordinator.api.connect()
        coordinator.api.setDepth(depth)
        coordinator.api.setDuration(duration)
        coordinator.api.setMode(mode)
        await coordinator.api.calibrate()
        await coordinator.api.disconnect()

    hass.services.async_register(DOMAIN, 'generate_token', generate_token)
    hass.services.async_register(DOMAIN, 'calibrate', calibrate)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True

class MicroBotDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the MicroBot."""

    def __init__(
        self, hass: HomeAssistant, client: MicroBotApiClient
    ) -> None:
        """Initialize."""
        self.api = client
        self.platforms = []

        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL)

    async def _async_update_data(self):
        """Update data via library."""
        try:
            return await self.api.async_get_data()
        except Exception as exception:
            raise UpdateFailed() from exception


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    unloaded = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in PLATFORMS
                if platform in coordinator.platforms
            ]
        )
    )
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
