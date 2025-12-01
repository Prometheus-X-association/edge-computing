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
import json
import logging
import os
import pathlib
import sys
import typing

from kubernetes import config

log = logging.getLogger(__name__)

DEF_SCHEDULER_NAME = "ptx-edge-scheduler"
DEF_SCHEDULER_METHOD = "random"
NS_CONFIG_FILE = "/var/run/secrets/kubernetes.io/serviceaccount/namespace"

CONFIG = {
    'method': os.getenv('METHOD', DEF_SCHEDULER_METHOD),
    'scheduler': os.getenv('SCHEDULER', DEF_SCHEDULER_NAME),
    'namespace': os.getenv('NAMESPACE')
}

REQUIRED_FIELDS = ('method', 'namespace', 'scheduler')


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


def param_parser(params: str = None) -> dict:
    """

    :param params:
    :return:
    """
    kv_dict = {}
    if params:
        for p in params.split(","):
            if len(kv := p.split('=', maxsplit=1)) == 2:
                k, v = kv
                try:
                    v = int(v) if v.isnumeric() else float(v) if '.' in v else v
                except ValueError:
                    pass
                kv_dict[k] = v
            else:
                log.warning(f"Invalid parameter format: {p}")
    return kv_dict
