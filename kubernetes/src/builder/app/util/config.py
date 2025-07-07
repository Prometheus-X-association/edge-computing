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
import tomllib
from typing import Generator

DEF_CFG_FILE = pathlib.Path("app/config.toml")
ENV_PREFIX_KEY = "prefix"
CONFIG = {}

log = logging.getLogger(__package__)


def deep_update(mapping: dict, *updating_mappings: dict) -> dict:
    """From pydantic's deep_update
    https://github.com/samuelcolvin/pydantic/blob/fd2991fe6a73819b48c906e3c3274e8e47d0f761/pydantic/utils.py#L200
    """
    updated = mapping.copy()
    for sub_mapping in updating_mappings:
        for k, v in sub_mapping.items():
            if k in updated and isinstance(updated[k], dict) and isinstance(v, dict):
                updated[k] = deep_update(updated[k], v)
            else:
                updated[k] = v
    return updated


def cfg_sections(data: dict) -> Generator[str, None, None]:
    for key in data:
        if isinstance(data[key], dict):
            yield from (f"{key:s}.{sub}" for sub in cfg_sections(data[key]))
        else:
            yield str(key)


def load_configuration(cfg_file: pathlib.Path | None) -> dict:
    # Load default config
    log.debug(f"Loading default configuration from {DEF_CFG_FILE.name}...")
    cfg = tomllib.loads(DEF_CFG_FILE.read_text(encoding="utf-8"))
    log.debug(f"Section(s) loaded: {list(cfg_sections(cfg))}")
    # Load additional config
    if cfg_file is not None:
        if not cfg_file.exists():
            raise FileNotFoundError(f"Configuration file {cfg_file} not found!")
        log.info(f"Loading configuration from {cfg_file.name}...")
        loaded_cfg = tomllib.loads(DEF_CFG_FILE.read_text(encoding="utf-8"))
        cfg = deep_update(cfg, loaded_cfg)
        log.debug(f"Section(s) loaded: {list(cfg_sections(loaded_cfg))}")
    # Load configuration from envvars
    if prefix := cfg.get('env', {}).get(ENV_PREFIX_KEY):
        log.debug(f"Loading configuration from envvars[{prefix}]...")
        env_cfg = '\n'.join((f'{k.lstrip(prefix).replace('_', '.').lower()} = "{v}"'
                             for k, v in os.environ.items() if k.startswith(prefix)))
        loaded_cfg = tomllib.loads(env_cfg)
        cfg = deep_update(cfg, tomllib.loads(env_cfg))
        log.debug(f"Section(s) loaded: {list(cfg_sections(loaded_cfg))}")
    global CONFIG
    CONFIG = cfg
    return cfg
