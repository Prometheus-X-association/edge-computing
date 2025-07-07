#!/usr/bin/env python3
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
import argparse
import logging
import pathlib

from . import __version__
from .util.config import load_configuration, DEF_CFG_FILE
from .util.helper import wait_and_exit, print_config, DEF_WAIT_SECONDS
from .util.logger import set_logging_level

log = logging.getLogger(__package__)


def main():
    # Parsing arguments
    parser = argparse.ArgumentParser(prog=pathlib.Path(__file__).name, description="PTX-edge builder")
    parser.add_argument("-d", "--dummy", action="store_true", required=False,
                        help=f"Wait for a specified time[{DEF_WAIT_SECONDS}s] and exit immediately.")
    parser.add_argument("-c", "--config", metavar="CFG", nargs='?', type=pathlib.Path, required=False,
                        help=f"Configuration file to be appended to the default config[{DEF_CFG_FILE}].")
    parser.add_argument("-v", "--verbose", action='count', default=0, required=False, help="Increase verbosity.")
    parser.add_argument("-V", "--version", action='version', version=f"{parser.description} v{__version__}")
    args = parser.parse_args()
    set_logging_level(verbosity=args.verbose)
    log.info("=== builder started ===")
    log.debug(args)
    # Load configuration
    cfg = load_configuration(cfg_file=args.config)
    print_config(cfg=cfg)
    # Testing builder
    if args.dummy:
        wait_and_exit()
    log.info("=== builder ended ===")


if __name__ == '__main__':
    main()
