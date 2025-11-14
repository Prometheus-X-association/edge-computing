# Copyright 2025 Janos Czentye
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
import typing

from benedict import benedict

DEF_CFG_FILE = pathlib.Path("app/config.toml")
CFG_ENV_PREFIX = "prefix"
# Global config object
CONFIG = benedict(keypath_separator='.', keyattr_dynamic=True)

log = logging.getLogger(__name__)


def isections(data: dict, sep: str = '.') -> typing.Generator[str, None, None]:
    """
    Generator for enlisting multi-level configuration sections

    :param data:
    :param sep:
    :return:
    """
    for key in data:
        if isinstance(data[key], dict):
            yield from (f"{key:s}{sep}{sub}" for sub in isections(data[key]))
        else:
            yield str(key)


def load_configuration(base: dict = None, cfg_file: pathlib.Path = None, from_env: bool = False) -> benedict:
    """
    Load configuration form multiple sources.

    :param base:
    :param cfg_file:
    :param from_env:
    :return:
    """
    if base is None:
        # Load default config from file
        if DEF_CFG_FILE.exists():
            log.debug(f"Loading default configuration from file: {DEF_CFG_FILE.name}...")
            cfg = benedict.from_toml(DEF_CFG_FILE.read_text(encoding="utf-8"))
            log.debug(f"Section(s) loaded: {list(isections(cfg))}")
        else:
            log.warning(f"No default configuration file found at {DEF_CFG_FILE.name}.")
            cfg = benedict()
    else:
        # Use given dict as the base configuration
        cfg = benedict(base)
        log.debug(f"Configuration section(s): {list(isections(cfg))}")
    # Load additional config from file
    if cfg_file is not None:
        if not cfg_file.exists():
            raise FileNotFoundError(f"Configuration file {cfg_file} not found!")
        log.info(f"Loading configuration file: {cfg_file.name}...")
        loaded_cfg = benedict.from_toml(cfg_file.read_text(encoding="utf-8"))
        cfg.merge(loaded_cfg, overwrite=True, concat=False)
        log.info(f"Section(s) loaded: {list(isections(loaded_cfg))}")
    # Load configuration from envvars
    if from_env:
        prefix = cfg.get('env', {}).get(CFG_ENV_PREFIX)
        log.debug(f"Loading configuration from envvars[{prefix}*]...")
        envvars = [(k, int(v)) if v.isnumeric() else (k, v) for k, v in os.environ.items() if k.startswith(prefix)]
        log.debug(f"Envvars found:\n{pprint.pformat(sorted(envvars))}")
        loaded_cfg = benedict.from_toml("\n".join(f'{k.removeprefix(prefix).replace('_', '.').lower()}="{v}"'
                                                  for k, v in envvars))
        cfg.merge(loaded_cfg, overwrite=True, concat=False)
        log.info(f"Section(s) loaded: {list(isections(loaded_cfg))}")
    # Cache config as a module parameter
    global CONFIG
    CONFIG.merge(cfg)
    # Print result
    print_config(CONFIG)
    return CONFIG


def print_config(cfg: benedict):
    log.debug("Builder configuration:\n" + cfg.to_toml())
