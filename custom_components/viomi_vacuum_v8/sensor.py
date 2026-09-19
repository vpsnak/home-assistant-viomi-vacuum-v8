"""Sensors for the Viomi Vacuum V8.

These do NOT talk to the vacuum themselves. The device answers exactly one
conversation at a time, so a second poller would fight the vacuum platform and
both would time out. Instead every sensor reads the state the vacuum entity has
already fetched, via hass.data[DATA_KEY].
"""
import logging

import voluptuous as vol

from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    EntityCategory,
    PERCENTAGE,
    UnitOfArea,
    UnitOfTime,
)
from homeassistant.core import callback
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

# key, label, source attribute, unit, device_class, state_class, icon, diagnostic
SENSORS = (
    ("battery", "Battery", "battary_life", PERCENTAGE,
     SensorDeviceClass.BATTERY, SensorStateClass.MEASUREMENT, None, False),
    ("cleaned_area", "Cleaned area", "s_area", UnitOfArea.SQUARE_METERS,
     None, SensorStateClass.MEASUREMENT, "mdi:texture-box", False),
    ("cleaning_time", "Cleaning time", "s_time", UnitOfTime.MINUTES,
     SensorDeviceClass.DURATION, SensorStateClass.MEASUREMENT, None, False),
    ("main_brush", "Main brush remaining", "main_brush_life", PERCENTAGE,
     None, SensorStateClass.MEASUREMENT, "mdi:car-turbocharger", False),
    ("side_brush", "Side brush remaining", "side_brush_life", PERCENTAGE,
     None, SensorStateClass.MEASUREMENT, "mdi:pinwheel-outline", False),
    ("hypa_filter", "Filter remaining", "hypa_filter_life", PERCENTAGE,
     None, SensorStateClass.MEASUREMENT, "mdi:air-filter", False),
    ("mop", "Mop remaining", "mop_life", PERCENTAGE,
     None, SensorStateClass.MEASUREMENT, "mdi:square-rounded", False),
    ("error", "Error code", "err_state", None,
     None, None, "mdi:alert-circle-outline", True),
    ("firmware", "Firmware", "sw_info", None,
     None, None, "mdi:chip", True),
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Attach sensors to the vacuum entity that is already set up."""
    host = config[CONF_HOST]
    name = config[CONF_NAME]

    vacuum_entity = (hass.data.get(DATA_KEY) or {}).get(host)
    if vacuum_entity is None:
        # The vacuum: platform has not run yet. HA will retry us.
        raise PlatformNotReady(
            f"Viomi vacuum at {host} is not set up yet - make sure the "
            f"`vacuum:` platform for the same host is configured."
        )

    async_add_entities(
        [ViomiSensor(name, host, vacuum_entity, *spec) for spec in SENSORS]
    )


class ViomiSensor(SensorEntity):
    """One value read off the vacuum entity's cached state."""

    _attr_should_poll = False

    def __init__(self, name, host, vacuum_entity, key, label, source, unit,
                 device_class, state_class, icon, diagnostic):
        self._vacuum_entity = vacuum_entity
        self._source = source
        self._attr_name = f"{name} {label}"
        self._attr_unique_id = f"{DATA_KEY}_{host}_{key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        if icon:
            self._attr_icon = icon
        if diagnostic:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self):
        return self._vacuum_entity.available

    @property
    def native_value(self):
        state = self._vacuum_entity.vacuum_state or {}
        value = state.get(self._source)
        if value is None:
            value = self._vacuum_entity.consumables.get(self._source)
        if value is None:
            return None
        if self._attr_state_class is None:
            return value
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @callback
    def _vacuum_updated(self, _event):
        """Mirror the vacuum entity's refresh. Must run in the event loop."""
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        """Refresh whenever the vacuum entity refreshes."""
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._vacuum_entity.entity_id],
                self._vacuum_updated,
            )
        )
