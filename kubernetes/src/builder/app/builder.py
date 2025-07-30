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
import json
import logging
import os
import pathlib
import sys

from app import __version__
from app.datasource import collect_data_from_file, collect_data_from_url, collect_data_from_ptx
from app.util.config import DEF_CFG_FILE, CONFIG, load_configuration, print_config
from app.util.helper import DEF_WAIT_SECONDS, wait_and_exit, get_resource_scheme, get_resource_path
from app.util.logger import set_logging_level
from app.worker import collect_worker_image_from_repo, configure_worker_credential, collect_worker_from_ptx

log = logging.getLogger(__package__)


def build() -> int:
    log.info("Building worker environment...")
    log.info("Obtaining input data...")
    timeout = CONFIG.get('connection.timeout', 30)
    ##########################################################################################
    data_src, data_dst = CONFIG['data.src'], CONFIG['data.dst']
    log.debug(f"Datasource is loaded from configuration: {data_src = }, {data_dst = }")
    match get_resource_scheme(data_src):
        case 'file' | 'local':
            data_path = collect_data_from_file(src=get_resource_path(data_src), dst=get_resource_path(data_dst))
        case 'http' | 'https':
            auth = CONFIG.get('data.src.auth')
            data_path = collect_data_from_url(url=data_src, dst=get_resource_path(data_dst),
                                              auth=auth, timeout=timeout)
        case 'ptx':
            data_path = collect_data_from_ptx(contract_id=get_resource_path(data_src),
                                              dst=get_resource_path(data_dst),
                                              timeout=timeout)
        case other:
            log.error(f"Unknown data source protocol: {other}")
            data_path = None
    if data_path is None:
        log.error("No data resource is collected. Abort builder...")
        return 1
    ##########################################################################################
    log.info("Obtaining worker configuration...")
    worker_src = CONFIG.get('worker.src')
    log.debug(f"Worker setup is loaded from configuration: {worker_src = }")
    if worker_src is None or worker_src.lower() in ('inline', 'datasource'):
        log.debug(f"Trying to load worker configuration from {data_path}...")
        with open(data_path, 'r') as f:
            worker_cfg = json.load(f)
        load_configuration(base=worker_cfg['worker'])
    worker_src, worker_dst = CONFIG['worker.src'], CONFIG['worker.dst']
    log.debug(f"Worker setup is loaded from configuration: {worker_src = }, {worker_dst = }")
    match get_resource_scheme(worker_src):
        case 'git':
            raise NotImplementedError
        case 'docker' | 'remote':
            auth = CONFIG.get('worker.src.auth')
            worker_path = collect_worker_image_from_repo(src=worker_src, dst=worker_dst, auth=auth, timeout=timeout)
        case 'auth' | 'secret':
            worker_path = configure_worker_credential(src=get_resource_path(worker_src),
                                                      dst=get_resource_path(worker_dst))
        case 'ptx':
            worker_path = collect_worker_from_ptx(contract_id=get_resource_path(data_src), dst=data_dst,
                                                  timeout=timeout)
        case other:
            log.error(f"Unknown data source protocol: {other}")
            worker_path = None
    if worker_path is None:
        log.error("No worker resource is collected. Abort builder...")
        return 1
    log.info("Worker environment built.")
    return 0


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
    cfg = load_configuration(cfg_file=args.config, from_env=True)
    print_config(cfg=cfg)
    if args.dummy:
        # Testing builder
        return wait_and_exit()
    try:
        # Invoke building functionality
        failed = build()
    except Exception as e:
        log.error(f"Build failed: {e}")
        sys.exit(os.EX_SOFTWARE)
    log.info(" builder ended ".center(60, '='))
    sys.exit(os.EX_DATAERR if failed else os.EX_OK)


if __name__ == '__main__':
    main()
