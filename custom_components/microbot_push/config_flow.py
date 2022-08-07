"""Adds config flow for MicroBot."""
from __future__ import annotations
import logging
import re
from typing import Any
from .api import MicroBotAdvertisement, parse_advertisement_data, MicroBotApiClient
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
import voluptuous as vol
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from .const import (
    CONF_NAME,
    CONF_BDADDR,
    DOMAIN,
    CONF_RETRY_COUNT, 
    DEFAULT_RETRY_COUNT, 
)

_LOGGER: logging.Logger = logging.getLogger(__package__)

def format_unique_id(address: str) -> str:
    """Format the unique ID for a switchbot."""
    return address.replace(":", "").lower()

class MicroBotConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for MicroBot."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> MicroBotOptionsFlowHandler:
        """Get the options flow for this handler."""
        return MicroBotOptionsFlowHandler(config_entry)

    def __init__(self):
        """Initialize."""
        self._errors = {}
        self._discovered_adv: MicrBotAdvertisement | None = None
        self._discovered_advs: dict[str, MicroBotAdvertisement] = {}
        self._client: None
        self._ble_device: None
        self._name = None
        self._bdaddr = None

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle the bluetooth discovery step."""
        _LOGGER.debug("Discovered bluetooth device: %s", discovery_info)
        await self.async_set_unique_id(format_unique_id(discovery_info.address))
        self._abort_if_unique_id_configured()
        parsed = parse_advertisement_data(
            discovery_info.device, discovery_info.advertisement
        )
        self._discovered_adv = parsed
        data = parsed.data
        self.context["title_placeholders"] = {
            "name": data["local_name"],
            "address": discovery_info.address,
        }
        return await self.async_step_init()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initialized by the user."""
        # This is for backwards compatibility.
        return await self.async_step_init(user_input)

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Check if paired."""
        errors: dict[str, str] = {}

        if discovery := self._discovered_adv:
            self._discovered_advs[discovery.address] = discovery
        else:
            current_addresses = self._async_current_ids()
            for discovery_info in async_discovered_service_info(self.hass):
                address = discovery_info.address
                if (
                    format_unique_id(address) in current_addresses
                    or address in self._discovered_advs
                ):
                    continue
                parsed = parse_advertisement_data(
                    discovery_info.device, discovery_info.advertisement
                )
                if parsed:
                    self._discovered_advs[address] = parsed

        if not self._discovered_advs:
            return self.async_abort(reason="no_unconfigured_devices")

        data_schema = vol.Schema(
            {
                vol.Required(CONF_BDADDR): vol.In(
                    {
                        address: f"{parsed.data['local_name']} ({address})"
                        for address, parsed in self._discovered_advs.items()
                    }
                ),
                vol.Required(CONF_NAME): str,
            }
        )

        if user_input is not None:
            self._name = user_input[CONF_NAME]
            self._bdaddr = user_input[CONF_BDADDR]
            await self.async_set_unique_id(
                format_unique_id(self._bdaddr), raise_on_progress=False
            )
            self._abort_if_unique_id_configured()
            self._ble_device = bluetooth.async_ble_device_from_address(self.hass, self._bdaddr.upper())
            if not self._ble_device:
                raise ConfigEntryNotReady(
                    f"Could not find MicroBot with address {self._bdaddr}"
            )
            conf = self.hass.config.path()+"/.storage/microbot-"+re.sub('[^a-f0-9]', '', self._bdaddr.lower())+".conf"
            self._client = MicroBotApiClient(
                device=self._ble_device,
                config=conf,
                retry_count=DEFAULT_RETRY_COUNT,
            )
            token = self._client.hasToken()
            if not token:
                return await self.async_step_link()       
            else:
                return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        return self.async_show_form(
            step_id="init", data_schema=data_schema, errors=errors
        )

    async def async_step_link(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Given a configured host, will ask the user to press the button to pair."""
        errors: dict[str, str] = {}
        token = self._client.hasToken()
        if user_input is None:
            try:
                await self._client.connect(init=True)
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception(
                    "Unknown error connecting with MicroBot"
                )
                errors["base"] = "linking"
            return self.async_show_form(step_id="link")

        if not token:
            errors:["base"] = "linking"

        if errors:
            return self.async_show_form(step_id="link", errors=errors)

        user_input[CONF_BDADDR] = self._bdaddr

        return self.async_create_entry(title=self._name, data=user_input)

class MicroBotOptionsFlowHandler(OptionsFlow):
    """Handle Microbot options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage Microbot options."""
        if user_input is not None:
            # Update common entity options for all other entities.
            return self.async_create_entry(title="", data=user_input)

        options = {
            vol.Optional(
                CONF_RETRY_COUNT,
                default=self.config_entry.options.get(
                    CONF_RETRY_COUNT, DEFAULT_RETRY_COUNT
                ),
            ): int
        }

        return self.async_show_form(step_id="init", data_schema=vol.Schema(options))
