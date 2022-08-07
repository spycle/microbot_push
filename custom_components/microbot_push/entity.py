"""MicroBot class"""
from __future__ import annotations
from homeassistant.components.bluetooth.passive_update_coordinator import (
    PassiveBluetoothCoordinatorEntity,
)
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, NAME, VERSION

class MicroBotEntity(PassiveBluetoothCoordinatorEntity):
    def __init__(self, coordinator, config_entry):
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._address = self.coordinator.ble_device.address
        self._attr_name = "MicroBot Push",
#        self._attr_name = self.coordinator.data["local_name"],
        self._attr_device_info = DeviceInfo(
            connections={(dr.CONNECTION_BLUETOOTH, self._address)},
            manufacturer="Keymitt/Naran",
            model="Push",
            name="MicroBot",
#            model=self.coordinator.data["local_name"],
#            name=self.coordinator.data["local_name"],
        )
        
    @property
    def unique_id(self):
        """Return a unique ID to use for this entity."""
        return self.config_entry.entry_id

#    @property
#    def device_info(self):
#        return {
#            "connection": {(dr.CONNECTION_BLUETOOTH, self.data["address"])},
#            "identifiers": {(DOMAIN, self.unique_id)},
#            "name": self.data["local_name"],
#            "model": self.data["local_name"],
#            "manufacturer": "Keymitt/Naran",
#        }

    @property
    def data(self) -> dict[str, Any]:
        """Return coordinator data for this entity."""
        return self.coordinator.data

#    @property
#    def extra_state_attributes(self):
#        """Return the state attributes."""
#        return {
#            "name": self.config_entry.data[CONF_NAME],
#            "id": str(self.coordinator.data.get("id")),
#            "integration": DOMAIN,
#        }
