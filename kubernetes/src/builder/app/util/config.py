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

from benedict import benedict

DEF_CFG_FILE = pathlib.Path("app/config.toml")
CFG_ENV_PREFIX = "prefix"
# Global config object
CONFIG = benedict(keypath_separator='.', keyattr_dynamic=True)

log = logging.getLogger(__package__)


def load_configuration(cfg_file: pathlib.Path = None) -> benedict:
    """
    Load configuration form multiple sources.

    :param cfg_file:
    :return:
    """
    # Load default config from file
    log.debug(f"Loading default configuration from {DEF_CFG_FILE.name}...")
    cfg = benedict.from_toml(DEF_CFG_FILE.read_text(encoding="utf-8"))
    log.debug(f"Section(s) loaded: {cfg.keypaths(sort=False)}")
    # Load additional config from file
    if cfg_file is not None:
        if not cfg_file.exists():
            raise FileNotFoundError(f"Configuration file {cfg_file} not found!")
        log.info(f"Loading configuration from {cfg_file.name}...")
        loaded_cfg = benedict.from_toml(cfg_file.read_text(encoding="utf-8"))
        cfg.merge(loaded_cfg, overwrite=True, concat=False)
        log.info(f"Section(s) loaded: {loaded_cfg.keypaths(sort=False)}")
    # Load configuration from envvars
    if prefix := cfg.get('env', {}).get(CFG_ENV_PREFIX):
        log.debug(f"Loading configuration from envvars[{prefix}*]...")
        envvars = [(k, v) for k, v in os.environ.items() if k.startswith(prefix)]
        log.debug(f"Envvars found:\n{pprint.pformat(envvars)}")
        loaded_cfg = benedict.from_toml("\n".join(f'{k.removeprefix(prefix).replace('_', '.').lower()}="{v}"'
                                                  for k, v in envvars))
        cfg.merge(loaded_cfg, overwrite=True, concat=False)
        log.info(f"Section(s) loaded: {loaded_cfg.keypaths(sort=False)}")
    # Cache config as a module parameter
    global CONFIG
    CONFIG.merge(cfg)
    return CONFIG


def print_config(cfg: benedict):
    log.debug("Builder configuration:\n" + cfg.to_toml())
