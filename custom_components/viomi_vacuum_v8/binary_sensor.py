"""Binary sensors for the Viomi Vacuum V8.

Like the sensors, these never talk to the vacuum. They read the state the
vacuum entity already fetched - the device only handles one conversation at a
time, so a second poller would make both time out.
"""
import logging

import voluptuous as vol

from homeassistant.components.binary_sensor import (
    PLATFORM_SCHEMA,
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import CONF_HOST, CONF_NAME, EntityCategory
from homeassistant.exceptions import PlatformNotReady
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import async_track_state_change_event

_LOGGER = logging.getLogger(__name__)

DATA_KEY = "viomi_vacuum_v8"
DEFAULT_NAME = "Viomi Vacuum V8"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    }
)

# key, label, source attribute, device_class, icon, diagnostic
BINARY_SENSORS = (
    ("charging", "Charging", "is_charge",
     BinarySensorDeviceClass.BATTERY_CHARGING, None, False),
    ("working", "Working", "is_work",
     BinarySensorDeviceClass.RUNNING, None, False),
    ("mop_attached", "Mop attached", "mop_type",
     None, "mdi:square-rounded", False),
    ("has_map", "Map stored", "has_map",
     None, "mdi:map-check", True),
)

# `is_charge` reads 0 while the vacuum sits on the dock and the battery climbs,
# so it is inverted relative to its name. Inferred from three readings on
# firmware 3.5.3_0017 (battery 10 -> 16 -> 22 %, is_charge 0, run_state 5
# docked throughout), not from any vendor documentation. If your unit reports
# the opposite, drop it from this set.
INVERTED = {"is_charge"}


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Attach binary sensors to the vacuum entity that is already set up."""
    host = config[CONF_HOST]
    name = config[CONF_NAME]

    vacuum_entity = (hass.data.get(DATA_KEY) or {}).get(host)
    if vacuum_entity is None:
        raise PlatformNotReady(
            f"Viomi vacuum at {host} is not set up yet - make sure the "
            f"`vacuum:` platform for the same host is configured."
        )

    async_add_entities(
        [ViomiBinarySensor(name, host, vacuum_entity, *spec)
         for spec in BINARY_SENSORS]
    )


class ViomiBinarySensor(BinarySensorEntity):
    """One boolean read off the vacuum entity's cached state."""

    _attr_should_poll = False

    def __init__(self, name, host, vacuum_entity, key, label, source,
                 device_class, icon, diagnostic):
        self._vacuum_entity = vacuum_entity
        self._source = source
        self._attr_name = f"{name} {label}"
        self._attr_unique_id = f"{DATA_KEY}_{host}_{key}"
        self._attr_device_class = device_class
        if icon:
            self._attr_icon = icon
        if diagnostic:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self):
        return self._vacuum_entity.available

    @property
    def is_on(self):
        state = self._vacuum_entity.vacuum_state or {}
        value = state.get(self._source)
        if value is None:
            return None
        try:
            on = bool(int(value))
        except (TypeError, ValueError):
            return None
        return not on if self._source in INVERTED else on

    async def async_added_to_hass(self):
        """Refresh whenever the vacuum entity refreshes."""
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._vacuum_entity.entity_id],
                lambda _event: self.async_write_ha_state(),
            )
        )
