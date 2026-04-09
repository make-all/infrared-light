"""
Setup for different kinds of Infrared controlled lights

Copyright 2026 Jason Rumney

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

"""

import logging
from typing import Optional

from homeassistant.components import infrared
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ColorMode,
    LightEntity,
)
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import slugify
from infrared_protocols.commands import Command, NECCommand

from .lib.common import load_config
from .lib.multi_command import MultiCommand
from .const import DOMAIN, CONF_CONFIG, CONF_INFRARED_ENTITY_ID

_LOGGER = logging.getLogger(__name__)

type InfraredLightEntityConfig = ConfigEntry[
    {
        "config_file": str,
    }
]


async def async_setup_entry(hass, config_entry, async_add_entities):
    light = await self.hass.async_add_executor_job(_create_light, config_entry)
    async_add_entities([light])


def _create_light(config_entry) -> InfraredLightEntity:
    return InfraredLightEntity(config_entry)


class InfraredLightEntity(LightEntity, RestoreEntity):
    """Representation of a Infrared controlled Light Entity."""

    def __init__(self, config_entry) -> None:
        """
        Initialise the light device.
        Args:
            device (TuyaLocalDevice): The device API instance
            config (TuyaEntityConfig): The entity config
        """
        super().__init__()
        _LOGGER.debug("Initializing Infrared Light with config: %s", config_entry.data)
        self._infrared_entity_id = config_entry.data[CONF_INFRARED_ENTITY_ID]
        config = load_config(config_entry.data[CONF_CONFIG])
        self._model = config.get("model", "Unknown")
        self._manufacturer = config.get("manufacturer", "Unknown")
        self._attr_unique_id = slugify(
            f"{DOMAIN}_{self._infrared_entity_id}_{self._manufacturer}_{self._model}"
        )
        self._attr_has_entity_name = True
        # Model is often the remote model, so just use manufacturer
        self._attr_name = None
        self._device_info = {
            "identifiers": {(DOMAIN, self._attr_unique_id)},
            "name": f"{self._manufacturer} IR light".strip(),
            "manufacturer": self._manufacturer,
            "model": self._model,
        }
        cmds = config.get("commands", {})
        if not cmds:
            _LOGGER.error(
                "%s config is missing commands",
                config_entry.data[CONF_INFRARED_ENTITY_ID],
            )
            raise AttributeError("Config is missing commands")
        codes = cmds.get("codes", {})
        if not codes:
            _LOGGER.error(
                "%s config is missing command codes",
                config_entry.data[CONF_INFRARED_ENTITY_ID],
            )
            raise AttributeError("Config is missing command codes")
        self._default_device = cmds.get("device")
        self._default_type = cmds.get("type")
        self._cmd = {}
        for cmd in codes:
            name = cmd.get("name")
            if not name:
                _LOGGER.error(
                    "%s command is missing a name %s",
                    config_entry.data[CONF_INFRARED_ENTITY_ID],
                    cmd,
                )
                raise AttributeError("Command is missing a name")
            self._cmd[name] = self._create_command(cmd)

        if "brightness_up" in self._cmd and "brightness_down" in self._cmd:
            self._attr_color_mode = ColorMode.BRIGHTNESS
            self._brightness_steps = config.get("brightness_steps", 1)

        if "color_temp_up" in self._cmd and "color_temp_down" in self._cmd:
            self._attr_min_color_temp_kelvin = config.get("color_temp_min", 2700)
            self._attr_max_color_temp_kelvin = config.get("color_temp_max", 6500)
            self._attr_color_mode = ColorMode.COLOR_TEMP
            self._color_temp_steps = config.get("color_temp_steps", 1)

        self._attr_supported_color_modes = {self._attr_color_mode}
        _LOGGER.debug("Finished initializing Infrared Light %s", self.name)

    def _create_command(self, cmd):
        """Create a Command from the config info"""
        type = cmd.get("type", self._default_type)
        device = cmd.get("device", self._default_device)
        code = cmd.get("code")
        repeat = cmd.get("repeat", 1)
        multi = cmd.get("multi")
        if multi:
            if not isinstance(multi, list):
                raise AttributeError("multi must be a list of commands to send")
            return MultiCommand([self._create_command(c) for c in multi])
        if type == "NECCommand":
            return NECCommand(
                address=device, command=code, repeat_count=repeat, modulation=38000
            )
        raise AttributeError(f"Unsupported command type {type}")

    def _brightness_to_step(self, brightness):
        """Convert a brightness value to a step index"""
        return round(brightness / (255 / self._brightness_steps))

    def _step_to_brightness(self, step):
        """Convert a step index to a brightness value"""
        return round(step * (255 / self._brightness_steps))

    def _color_temp_to_step(self, color_temp):
        """Convert a color temp value to a step index"""
        return round(
            (color_temp - self._attr_min_color_temp_kelvin)
            / (
                (self._attr_max_color_temp_kelvin - self._attr_min_color_temp_kelvin)
                / self._color_temp_steps
            )
        )

    def _step_to_color_temp(self, step):
        """Convert a step index to a color temp value"""
        return round(
            step
            * (
                (self._attr_max_color_temp_kelvin - self._attr_min_color_temp_kelvin)
                / self._color_temp_steps
            )
            + self._attr_min_color_temp_kelvin
        )

    async def _async_send_command(self, cmd):
        """Send a command to the device"""
        await infrared.async_send_command(
            self.hass, self._infrared_entity_id, cmd, context=self._context
        )

    async def async_turn_on(self, **kwargs):
        """Turn the light on."""
        did_something = False

        # turn on if off and we have a command for it
        if self._attr_is_on is not True and "turn_on" in self._cmd:
            await self._async_send_command(self._cmd["turn_on"])
            self._attr_is_on = True
            did_something = True

        # if brightness is 1, we treat that as nightlight mode and send the nightlight command if we have one
        if (
            ATTR_BRIGHTNESS in kwargs
            and kwargs[ATTR_BRIGHTNESS] == 1
            and self._cmd.get("nightlight")
        ):
            await self._async_send_command(self._cmd["nightlight"])
            self._attr_brightness = 1
            did_something = True

        elif (
            ATTR_BRIGHTNESS in kwargs
            and self._cmd.get("brightness_up")
            and self._cmd.get("brightness_down")
        ):
            brightness = kwargs[ATTR_BRIGHTNESS]
            target = self._brightness_to_step(brightness)
            current = self._brightness_to_step(self._attr_brightness or 0)
            if target == 0 or target == self._brightness_steps - 1:
                # If target is at the end of the range, resync
                steps = self._brightness_steps - 1
            else:
                steps = abs(target - current)

            if target < current:
                cmd = self._cmd["brightness_down"]
            else:
                cmd = self._cmd["brightness_up"]
            if steps == 1:
                await self._async_send_command(cmd)
                self._attr_brightness = self._step_to_brightness(target)
                did_something = True
            elif steps > 1:
                cmd_list = []
                for i in range(int(steps)):
                    cmd_list.append(cmd)
                await self._async_send_command(MultiCommand(cmd_list))
                self._attr_brightness = self._step_to_brightness(target)
                did_something = True

        if (
            ATTR_COLOR_TEMP_KELVIN in kwargs
            and self._cmd.get("color_temp_up")
            and self._cmd.get("color_temp_down")
        ):
            color_temp = kwargs[ATTR_COLOR_TEMP_KELVIN]
            target = self._color_temp_to_step(color_temp)
            current = self._color_temp_to_step(
                self._attr_color_temp_kelvin or self._attr_min_color_temp_kelvin
            )
            if target == 0 or target == self._color_temp_steps - 1:
                # If target is at the end of the range, resync
                steps = self._color_temp_steps - 1
            else:
                steps = abs(target - current)
            if target < current:
                cmd = self._cmd["color_temp_down"]
            else:
                cmd = self._cmd["color_temp_up"]

            if steps == 1:
                await self._async_send_command(cmd)
                self._attr_color_temp_kelvin = self._step_to_color_temp(target)
                did_something = True
            elif steps > 1:
                cmd_list = []
                for i in range(int(steps)):
                    cmd_list.append(cmd)
                await self._async_send_command(MultiCommand(cmd_list))
                self._attr_color_temp_kelvin = self._step_to_color_temp(target)
                did_something = True

        # If we didn't send any command, send an on command to ensure the light is in sync
        if not did_something and "turn_on" in self._cmd:
            await self._async_send_command(self._cmd["turn_on"])
            self._attr_is_on = True

        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the light off."""
        if "turn_off" in self._cmd:
            await self._async_send_command(self._cmd["turn_off"])
            self._attr_is_on = False
            self.async_write_ha_state()
