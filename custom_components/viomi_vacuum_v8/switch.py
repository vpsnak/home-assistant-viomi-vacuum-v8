"""Switches for the Viomi Vacuum V8.

Reads come from the state the vacuum entity already fetched (the device only
handles one conversation at a time). Writes go through the same device handler,
in an executor because the miio call is blocking.

`set_repeat` was verified against firmware 3.5.3_0017: sending [1] then reading
`repeat_state` back returns 1, and [0] returns 0.
"""
import logging

import voluptuous as vol

from homeassistant.components.switch import (
    PLATFORM_SCHEMA,
    SwitchDeviceClass,
    SwitchEntity,
)
from homeassistant.const import CONF_HOST, CONF_NAME
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

# key, label, source attribute, miio setter, icon
SWITCHES = (
    ("repeat", "Repeat cleaning", "repeat_state", "set_repeat",
     "mdi:repeat-variant"),
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Attach switches to the vacuum entity that is already set up."""
    host = config[CONF_HOST]
    name = config[CONF_NAME]

    vacuum_entity = (hass.data.get(DATA_KEY) or {}).get(host)
    if vacuum_entity is None:
        raise PlatformNotReady(
            f"Viomi vacuum at {host} is not set up yet - make sure the "
            f"`vacuum:` platform for the same host is configured."
        )

    async_add_entities(
        [ViomiSwitch(name, host, vacuum_entity, *spec) for spec in SWITCHES]
    )


class ViomiSwitch(SwitchEntity):
    """A boolean device setting, read from cache and written over miio."""

    _attr_should_poll = False
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, name, host, vacuum_entity, key, label, source, setter, icon):
        self._vacuum_entity = vacuum_entity
        self._source = source
        self._setter = setter
        self._attr_name = f"{name} {label}"
        self._attr_unique_id = f"{DATA_KEY}_{host}_{key}"
        self._attr_icon = icon

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
            return bool(int(value))
        except (TypeError, ValueError):
            return None

    async def _set(self, value):
        device = self._vacuum_entity.device
        await self.hass.async_add_executor_job(
            device.raw_command, self._setter, [value]
        )
        # pull fresh state so the UI does not sit on the old value
        await self._vacuum_entity.async_update_ha_state(True)

    async def async_turn_on(self, **kwargs):
        await self._set(1)

    async def async_turn_off(self, **kwargs):
        await self._set(0)

    @callback
    def _vacuum_updated(self, _event):
        """Mirror the vacuum entity's refresh. Must run in the event loop."""
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._vacuum_entity.entity_id],
                self._vacuum_updated,
            )
        )
