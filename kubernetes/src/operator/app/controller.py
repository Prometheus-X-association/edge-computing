#!/usr/bin/env python3
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
from kubernetes import config

from app import __version__
from app.utils import setup_logging

log = logging.getLogger(__name__)

NS_CONFIG_FILE = "/var/run/secrets/kubernetes.io/serviceaccount/namespace"

CONFIG = {}

REQUIRED_FIELDS = ()


def serve_forever(param):
    kopf.run()


def setup_config(params: dict[str, typing.Any]):
    """

    :param params:
    :return:
    """
    log.info("Loading configuration...")
    CONFIG.update(kv for kv in params.items() if kv[1] is not None)
    if CONFIG.get('namespace') is None and (kube_cfg_ns := pathlib.Path(NS_CONFIG_FILE).resolve(strict=True)).exists():
        CONFIG['namespace'] = kube_cfg_ns.read_text()
    if not all(map(lambda param: bool(CONFIG[param]), REQUIRED_FIELDS)):
        log.error(f"Missing one of the required parameters: {REQUIRED_FIELDS} from {CONFIG}")
        sys.exit(os.EX_CONFIG)
    log.debug(f"Loaded configuration:\n{json.dumps(CONFIG, indent=4, default=str)}")
    try:
        log.debug("Loading in-cluster K8s configuration....")
        config.load_incluster_config()
    except config.ConfigException as e:
        log.error(f"Error loading Kubernetes API config:\n{e}")
        sys.exit(os.EX_CONFIG)


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
    try:
        serve_forever(**CONFIG)
    except Exception as e:
        log.error(f"Unexpected error received:\n{e}")
        log.exception(e)
        sys.exit(os.EX_SOFTWARE)


if __name__ == '__main__':
    main()
