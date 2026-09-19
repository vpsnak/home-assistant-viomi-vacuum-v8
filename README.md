# Home Assistant — Viomi Vacuum V8 (STYJ02YM)

Fork of [tykarol/home-assistant-viomi-vacuum-v8](https://github.com/tykarol/home-assistant-viomi-vacuum-v8),
kept working on current Home Assistant and extended with real entities instead
of a pile of attributes.

Fully **local** — `local_polling`, no cloud account, no 2FA. It needs only the
device IP and its miio token.

## Why this fork

Upstream stopped at HA 2026.6 and the fixes have been sitting in unmerged PRs
(#15, #16). On **HA 2026.9** the integration will not even import. Three things
changed in Home Assistant:

| Breakage | Fix here |
|---|---|
| `STATE_*` vacuum constants removed | rebuilt from the `VacuumActivity` enum |
| `StateVacuumEntity.state` became `@final` | the property is now `activity` |
| `VacuumEntityFeature.BATTERY` removed | dropped from the feature flags; battery is a sensor now |

## What this fork adds

`get_consumables` was never exposed. It is now, plus proper entities:

**Sensors** — battery, cleaned area, cleaning time, main brush / side brush /
HEPA filter / mop remaining (%), error code, firmware.

**Binary sensors** — charging, working, mop attached, map stored.

None of them poll the vacuum. The device answers exactly one conversation at a
time: a second poller makes both time out. They all read the state the `vacuum`
platform already fetched, through `hass.data`.

## Configuration

```yaml
vacuum:
  - platform: viomi_vacuum_v8
    host: 192.168.1.61
    token: !secret viomi_token
    name: My Vacuum

sensor:
  - platform: viomi_vacuum_v8
    host: 192.168.1.61        # same host as the vacuum above
    name: My Vacuum

binary_sensor:
  - platform: viomi_vacuum_v8
    host: 192.168.1.61
    name: My Vacuum
```

The `sensor` and `binary_sensor` platforms are optional and attach to the
`vacuum` entity with the same `host`.

## Getting the token

The miio token is local to the device. It changes whenever the vacuum is
re-paired in the Mi Home app.

## Consumable lifetimes

`get_consumables` returns hours used, in order: main brush, side brush, HEPA
filter, mop. The percentages assume 360 h for the main brush and 180 h for the
other three — the values the Mi Home app resets against.
