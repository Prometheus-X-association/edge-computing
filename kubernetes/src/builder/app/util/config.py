# Copyright 2024 Janos Czentye
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging
import os
import pathlib
import pprint
import tomllib
from typing import Generator

DEF_CFG_FILE = pathlib.Path("app/config.toml")
CFG_ENV_PREFIX = "prefix"
# Global config object
CONFIG = {}

log = logging.getLogger(__package__)


def deep_update(base: dict, *mapping: dict) -> dict:
    """Based on pydantic's deep_update function:
    https://github.com/samuelcolvin/pydantic/blob/fd2991fe6a73819b48c906e3c3274e8e47d0f761/pydantic/utils.py#L200
    """
    new = base.copy()
    for sub in mapping:
        for k, v in sub.items():
            new[k] = deep_update(new[k], v) if k in new and isinstance(new[k], dict) and isinstance(v, dict) else v
    return new


def get_cfg_sections(data: dict) -> Generator[str, None, None]:
    """
    Generator for enlisting multi-level configuration sections
    :param data:
    :return:
    """
    for key in data:
        if isinstance(data[key], dict):
            yield from (f"{key:s}.{sub}" for sub in get_cfg_sections(data[key]))
        else:
            yield str(key)


def load_configuration(cfg_file: pathlib.Path | None) -> dict:
    """
    Load configuration form multiple sources.

    :param cfg_file:
    :return:
    """
    # Load default config from file
    log.debug(f"Loading default configuration from {DEF_CFG_FILE.name}...")
    cfg = tomllib.loads(DEF_CFG_FILE.read_text(encoding="utf-8"))
    log.debug(f"Section(s) loaded: {list(get_cfg_sections(cfg))}")
    # Load additional config from file
    if cfg_file is not None:
        if not cfg_file.exists():
            raise FileNotFoundError(f"Configuration file {cfg_file} not found!")
        log.info(f"Loading configuration from {cfg_file.name}...")
        loaded_cfg = tomllib.loads(DEF_CFG_FILE.read_text(encoding="utf-8"))
        cfg = deep_update(cfg, loaded_cfg)
        log.info(f"Section(s) loaded: {list(get_cfg_sections(loaded_cfg))}")
    # Load configuration from envvars
    if prefix := cfg.get('env', {}).get(CFG_ENV_PREFIX):
        log.debug(f"Loading configuration from envvars[{prefix}*]...")
        env_items = [f'{k.removeprefix(prefix).replace('_', '.').lower()} = "{v}"'
                     for k, v in os.environ.items() if k.startswith(prefix)]
        log.debug(f"Configuration found:\n{pprint.pformat(env_items, indent=4)}")
        loaded_cfg = tomllib.loads("\n".join(env_items))
        cfg = deep_update(cfg, loaded_cfg)
        log.info(f"Section(s) loaded: {list(get_cfg_sections(loaded_cfg))}")
    # Cache config as a module parameter
    global CONFIG
    CONFIG.update(cfg)
    return cfg
