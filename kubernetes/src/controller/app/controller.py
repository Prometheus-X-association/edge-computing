#!/usr/bin/env python3
# Copyright 2026 Janos Czentye
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
import typing

import kopf

from utils import setup_logging

__version__ = '1.0.0'
log = logging.getLogger(__name__)

NS_CONFIG_FILE = "/var/run/secrets/kubernetes.io/serviceaccount/namespace"

REQUIRED_FIELDS = ()
CONFIG = {}


@kopf.on.create('edgeworkertasks')
def create_ewt(spec, **kwargs):
    print("Creation completed.")
    print(f"And here we are! Creating: {spec}")
    log.debug(f"log-Creation completed.")
    return {'message': 'hello world'}  # will be the new status


def setup_config(params: dict[str, typing.Any]):
    """

    :param params:
    :return:
    """
    log.info("Loading configuration...")
    CONFIG.update(kv for kv in params.items() if kv[1] is not None)
    if CONFIG.get('namespace') is None and (kube_cfg_ns := pathlib.Path(NS_CONFIG_FILE).resolve()).exists():
        CONFIG['namespace'] = kube_cfg_ns.read_text()
    if not all(map(lambda param: bool(CONFIG[param]), REQUIRED_FIELDS)):
        log.error(f"Missing one of the required parameters: {REQUIRED_FIELDS} from {CONFIG}")
        sys.exit(os.EX_CONFIG)
    # TODO - optional configs
    log.debug(f"Loaded configuration:\n{json.dumps(CONFIG, indent=4, default=str)}")


def main():
    ################# Parse parameters
    parser = argparse.ArgumentParser(prog=pathlib.Path(__file__).name, description="PTX-edge custom scheduler")
    parser.add_argument("-n", "--namespace", type=str, required=False,
                        help="Watched worker namespace (def: from kube cfg/envvar)")
    parser.add_argument("-v", "--verbose", action='count', default=0, required=False,
                        help="Increase verbosity")
    parser.add_argument("-V", "--version", action='version', version=f"{parser.description} v{__version__}")
    args = parser.parse_args()
    ################# Setup configuration
    setup_logging(verbosity=args.verbose)
    setup_config(params=vars(args))
    ################# Handle scheduling events
    log.debug(f"Initialization completed.")


if __name__ == '__main__':
    main()
