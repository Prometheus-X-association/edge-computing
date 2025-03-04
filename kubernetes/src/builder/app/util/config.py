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
import configparser
import logging
import pathlib

DEF_CFG_FILE = pathlib.Path("config.ini")

log = logging.getLogger(__package__)

def load_configuration(cfg_file: pathlib.Path | None) -> configparser.ConfigParser:
    # Load default config
    log.info(f"Loading configuration from {DEF_CFG_FILE.name}...")
    parser = configparser.ConfigParser()
    sections = parser.read(DEF_CFG_FILE)
    log.debug(f"Section loaded: {sections}")
    # Load additional config
    if cfg_file is not None:
        if not cfg_file.exists():
            raise FileNotFoundError(f"Configuration file {cfg_file} not found")
        log.info(f"Loading configuration from {cfg_file.name}...")
        parser = configparser.ConfigParser()
        sections = parser.read(cfg_file)
        log.debug(f"Section loaded: {sections}")
    return parser
