"""Switch platform for MicroBot."""
from homeassistant.components.switch import SwitchEntity

from .const import DEFAULT_NAME, DOMAIN, ICON, SWITCH
from .entity import MicroBotEntity

async def async_setup_entry(hass, entry, async_add_devices):
    """Setup switch platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_devices([MicroBotBinarySwitch(coordinator, entry)])

class MicroBotBinarySwitch(MicroBotEntity, SwitchEntity):
    """MicroBot switch class."""

    async def async_turn_on(self, **kwargs):  # pylint: disable=unused-argument
        """Turn on the switch."""
        await self.coordinator.api.connect()
        await self.coordinator.api.push()
        await self.coordinator.api.disconnect()

    async def async_turn_off(self, **kwargs):  # pylint: disable=unused-argument
        """Turn off the switch."""
        await self.coordinator.api.connect()
        await self.coordinator.api.push()
        await self.coordinator.api.disconnect()

    @property
    def name(self):
        """Return the name of the switch."""
        return f"{DEFAULT_NAME}"

    @property
    def icon(self):
        """Return the icon of this switch."""
        return ICON

    @property
    def is_on(self):
        """Return true if the switch is on."""
#        return self.coordinator.data.get("title", "") == "foo"
#        state = self.coordinator.api.on_state()
        return

    @property
    def available(self) -> bool:
        return True

    @property
    def assumed_state(self) -> bool:
        return False
