#!/usr/bin/env python3
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
import argparse
import logging
import os
import pathlib
import sys

from app import __version__
from app.datasource import get_data_resources
from app.util.config import load_configuration
from app.util.dummy import wait_and_exit
from app.util.logger import set_logging_level
from app.worker import get_worker_resources

log = logging.getLogger(__name__)


def build() -> bool:
    """

    :return:
    """
    log.info("Building worker environment...")
    data_path = get_data_resources()
    if data_path is None:
        log.error("No data resource is collected. Abort builder...")
        return False
    else:
        log.info(f"Collected data resources: {data_path}")
    result = get_worker_resources(data_path)
    if result is None:
        log.error("No worker configuration is collected. Abort builder...")
        return False
    else:
        log.info(f"Worker is configured successfully!")
    log.info("Worker environment has been built successfully.")
    return True


def main():
    # Parsing arguments
    parser = argparse.ArgumentParser(prog=pathlib.Path(__file__).name, description="PTX-edge builder")
    parser.add_argument("-d", "--dummy", action="store_true", required=False,
                        help=f"Wait for a specified time and exit immediately.")
    parser.add_argument("-c", "--config", metavar="CFG", nargs='?', type=pathlib.Path, required=False,
                        help=f"Configuration file to be appended to the default config.")
    parser.add_argument("-v", "--verbose", action='count', default=0, required=False,
                        help="Increase verbosity.")
    parser.add_argument("-V", "--version", action='version',
                        version=f"{parser.description} v{__version__}")
    args = parser.parse_args()
    set_logging_level(verbosity=args.verbose)
    log.info(" builder START ".center(80, '='))
    log.debug("Configuration arguments: %s", args)
    # Load configuration
    load_configuration(cfg_file=args.config, from_env=True)
    if args.dummy:
        # Testing builder
        return wait_and_exit()
    try:
        # Invoke building functionality
        success = build()
    except Exception as e:
        log.error(f"Build failed unexpectedly: {e}")
        if args.verbose:
            log.exception(e)
        sys.exit(os.EX_SOFTWARE)
    log.info(" builder END ".center(80, '='))
    sys.exit(os.EX_OK if success else os.EX_SOFTWARE)


if __name__ == '__main__':
    main()
