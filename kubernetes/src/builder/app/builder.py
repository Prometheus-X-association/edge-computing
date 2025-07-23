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

from app import __version__
from app.datasource import *
from app.util.config import load_configuration, DEF_CFG_FILE, CONFIG
from app.util.helper import wait_and_exit, print_config, DEF_WAIT_SECONDS, get_datasource_scheme, get_datasource_path
from app.util.logger import set_logging_level

log = logging.getLogger(__package__)


def build():
    log.info("Building worker environment...")
    data_src, data_dst = CONFIG['data']['src'].strip(), CONFIG['data']['dst'].strip()
    log.debug(f"{data_src = }, {data_dst = }")
    match get_datasource_scheme(data_src):
        case 'ptx':
            collect_data_from_ptx(contract_id=get_datasource_path(data_src), dst=data_dst)
        case 'http' | 'https':
            collect_data_from_url(url=data_src, dst=data_dst)
        case 'file' | 'local':
            collect_data_from_file(src_file=get_datasource_path(data_src), dst=data_dst)
        case other:
            raise Exception(f"Unknown data source protocol: {other}")
    log.info("Worker environment finished")


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
    log.info(" builder started ".center(60, '='))
    log.debug(args)
    # Load configuration
    cfg = load_configuration(cfg_file=args.config)
    print_config(cfg=cfg)
    if args.dummy:
        # Testing builder
        wait_and_exit()
    else:
        # Invoke building functionality
        build()
    log.info(" builder ended ".center(60, '='))


if __name__ == '__main__':
    main()
