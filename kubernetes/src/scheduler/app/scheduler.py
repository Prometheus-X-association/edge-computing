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

from kubernetes import client, config, watch

from app import __version__
from app.k8s import assign_pod_to_node
from app.method.rand import do_random_pod_assignment
from app.utils import setup_logging

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


def schedule_pod(pod_name: str, namespace: str, method: str) -> str:
    """

    :param pod_name:
    :param namespace:
    :param method:
    :return:
    """
    log.info(f"Scheduling pod[{pod_name}] in namespace: {namespace} using method: {method}...")
    match method:
        case 'random':
            node = do_random_pod_assignment()
        case _:
            log.error(f"Unknown scheduler method: {method}")
            sys.exit(os.EX_USAGE)
    ret = assign_pod_to_node(pod_name=pod_name, node_name=node, namespace=namespace) if node is not None else None
    return "Success" if ret is not None else "Failed"


def serve_forever(scheduler: str, namespace: str, method: str, **kwargs):
    """

    :param scheduler:
    :param namespace:
    :param method:
    :param kwargs:
    :return:
    """
    log.info(f"Scheduler[{scheduler}] is listening on namespace: {namespace}...")
    watcher = watch.Watch()
    try:
        pod_filter = f"spec.schedulerName={scheduler},status.phase=Pending"
        for event in watcher.stream(client.CoreV1Api().list_namespaced_pod, namespace, field_selector=pod_filter):
            _type, _pod = event['type'], event['object']
            _name = _pod.metadata.name
            log.debug(f"Received event: {_pod.kind}[{_name}] {_type} --> "
                      f"{_pod.status.phase} on node: {_pod.status.phase}")
            if _type != 'ADDED':
                continue
            try:
                log.info(f"{_type} pod[{_name}] in namespace[{namespace}] with scheduler[{scheduler}] detected!")
                result = schedule_pod(pod_name=_name, namespace=namespace, method=method)
                log.debug(f"Received scheduling result: {result}")
            except client.OpenApiException as e:
                log.error(f"API exception received:\n{e}")
    except KeyboardInterrupt:
        pass
    finally:
        watcher.stop()
        log.info("Stop watching for pod scheduling events")


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


def main():
    ################# Parse parameters
    parser = argparse.ArgumentParser(prog=pathlib.Path(__file__).name, description="PTX-edge custom scheduler")
    parser.add_argument("-m", "--method", type=str, default=DEF_SCHEDULER_METHOD,
                        help=f"Applied scheduling method (def: {DEF_SCHEDULER_METHOD})")
    parser.add_argument("-n", "--namespace", type=str, required=False,
                        help="Watched worker namespace (def: from kube cfg/envvar)")
    parser.add_argument("-s", "--scheduler", type=str, required=False, default=DEF_SCHEDULER_NAME,
                        help=f"Scheduler name referenced by worker pods (def: {DEF_SCHEDULER_NAME})")
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
