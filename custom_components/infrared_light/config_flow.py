"""
Config flow for the infrared_light integration.

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
from typing import Any

import voluptuous as vol
from homeassistant.components.infrared import (
    DOMAIN as INFRARED_DOMAIN,
)
from homeassistant.components.infrared import (
    async_get_emitters,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import CONF_CONFIG, CONF_INFRARED_ENTITY_ID, DOMAIN
from .lib.common import list_config_options, load_config

_LOGGER = logging.getLogger(__name__)


class ConfigFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the infrared_light integration."""

    VERSION = 1
    MINOR_VERSION = 0

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the user config step."""
        if user_input is not None:
            emitter_id = user_input[CONF_INFRARED_ENTITY_ID]
            config_file = user_input[CONF_CONFIG]
            await self.async_set_unique_id(f"ir_light_{config_file}_{emitter_id}")
            self._abort_if_unique_id_configured()

            registry = er.async_get(self.hass)
            emitter_entry = registry.async_get(emitter_id)
            emitter = (
                emitter_entry.name or emitter_entry.original_name or emitter_id
                if emitter_entry
                else emitter_id
            )
            try:
                config_contents = await self.hass.async_add_executor_job(
                    load_config, config_file
                )
            except Exception as e:
                _LOGGER.error("Error loading config file %s: %s", config_file, e)
                return self.async_abort(reason="invalid_config_file")

            # Get title from config
            manufacturer = config_contents.get("manufacturer", "Unknown")
            model = config_contents.get("model", "")
            title = config_contents.get(
                "name", f"{manufacturer} {model} IR light controlled via {emitter}"
            )
            # Process the user input and create the config entry
            return self.async_create_entry(
                title=title,
                data={**user_input, "manufacturer": manufacturer, "model": model},
            )

        emitters = async_get_emitters(self.hass)
        if not emitters:
            return self.async_abort(reason="no_infrared_emitters")

        configs = await self.hass.async_add_executor_job(list_config_options)

        # Show the form to the user
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CONFIG): SelectSelector(
                        SelectSelectorConfig(
                            options=configs,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Required(CONF_INFRARED_ENTITY_ID): EntitySelector(
                        EntitySelectorConfig(
                            domain=INFRARED_DOMAIN,
                            include_entities=emitters,
                        )
                    ),
                }
            ),
        )
