"""
Custom integration to integrate MicroBot with Home Assistant.

For more details about this integration, please refer to
https://github.com/spycle/microbot_push
"""
from __future__ import annotations
import asyncio
from datetime import timedelta
import logging
import re
from typing import TYPE_CHECKING, Any

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Config, HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.components.bluetooth.passive_update_coordinator import (
    PassiveBluetoothDataUpdateCoordinator,
)
from .api import MicroBotApiClient, parse_advertisement_data
from .api import GetMicroBotDevices

if TYPE_CHECKING:
    from bleak.backends.device import BLEDevice

from .const import (
    CONF_BDADDR,
    CONF_NAME,
    DOMAIN,
    PLATFORMS,
    STARTUP_MESSAGE,
    CONF_RETRY_COUNT,
    DEFAULT_RETRY_COUNT,
)

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup(hass: HomeAssistant, config: Config):
    """Set up this integration using YAML is not supported."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up this integration using UI."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})
        _LOGGER.debug(STARTUP_MESSAGE)

    if not entry.options:
        hass.config_entries.async_update_entry(
            entry,
            options={CONF_RETRY_COUNT: DEFAULT_RETRY_COUNT},
        )
    bdaddr = entry.data.get(CONF_BDADDR)
    ble_device = bluetooth.async_ble_device_from_address(hass, bdaddr.upper())
    if not ble_device:
        raise ConfigEntryNotReady(
            f"Could not find MicroBot with address {bdaddr}"
        )
    name = entry.data.get(CONF_NAME)
    conf_dir = hass.config.path()
    conf = conf_dir+"/.storage/microbot-"+re.sub('[^a-f0-9]', '', bdaddr.lower())+".conf"
    client = MicroBotApiClient(
        device=ble_device,
        config=conf,
        retry_count=entry.options[CONF_RETRY_COUNT],
    )
    coordinator = MicroBotDataUpdateCoordinator(hass, client=client, ble_device=ble_device)

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

class MicroBotDataUpdateCoordinator(PassiveBluetoothDataUpdateCoordinator):
    """Class to manage fetching data from the MicroBot."""

    def __init__(
        self, hass: HomeAssistant, client: MicroBotApiClient, ble_device: BLEDevice,
    ) -> None:
        """Initialize."""
        self.api = client
        self.platforms = []
        self._ready_event = asyncio.Event()
        self.data: dict[str, Any] = {}
        self.ble_device = ble_device

        super().__init__(
            hass, _LOGGER, ble_device.address, bluetooth.BluetoothScanningMode.ACTIVE
        )

    @callback
    def _async_handle_bluetooth_event(
        self,
        service_info: bluetooth.BluetoothServiceInfoBleak,
        change: bluetooth.BluetoothChange,
    ) -> None:
        """Handle a Bluetooth event."""
        super()._async_handle_bluetooth_event(service_info, change)
        if adv := parse_advertisement_data(
            service_info.device, service_info.advertisement
        ):
            self.data = adv.data
            if self.data:
                self._ready_event.set()
            _LOGGER.debug("%s: MicroBot data: %s", self.ble_device.address, self.data)
            self.device.update_from_advertisement(adv)
        self.async_update_listeners()

    async def async_wait_ready(self) -> bool:
        """Wait for the device to be ready."""
        try:
            await asyncio.wait_for(self._ready_event.wait(), timeout=55)
        except asyncio.TimeoutError:
            return False
        return True

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
