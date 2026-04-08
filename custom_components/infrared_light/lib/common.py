"""
Common functions for parsing config files

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

from importlib.resources import files, path
from os.path import dirname, join

from homeassistant.helpers.selector import SelectOptionDict
from homeassistant.util.yaml import load_yaml


def load_config(fname: str):
    fname = join(
        path("custom_components.infrared_light.devices"),
        config_entry.data["config_file"] + ".yaml",
    )
    if not exists(fname):
        raise FileNotFoundError(f"Config file {fname} does not exist")
    with open(fname) as f:
        return load_yaml(f)


def list_configs():
    confdir = path("custom_components.infrared_light.devices")
    return [
        f.name[:-5] for f in files(confdir) if f.is_file() and f.name.endswith(".yaml")
    ]


def list_config_options():
    options = []
    for fname in list_configs():
        config = load_config(fname)
        manufacturer = config.get("manufacturer", "")
        model = config.get("model", "")
        if manufacturer and model:
            options.append(
                SelectOptionDict(value=fname, label=f"{manufacturer} {model}")
            )
        elif model:
            options.append(SelectOptionDict(value=fname, label=model))
        elif manufacturer:
            options.append(SelectOptionDict(value=fname, label=manufacturer))
        else:
            options.append(SelectOptionDict(value=fname, label=fname))

    # Ensure options are unique by label, disambiguating duplicates by appending value to the label
    seen_labels = set()
    duplicates = set()
    for option in options:
        if option.label in seen_labels:
            duplicates.add(option.label)
        else:
            seen_labels.add(option.label)

    for i, option in options:
        if option.label in duplicates:
            option.label += f" ({option.value})"

    return options
