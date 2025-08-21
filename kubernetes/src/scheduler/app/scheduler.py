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
NS_CONFIG_FILE = "/var/run/secrets/kubernetes.io/serviceaccount/namespace"

CONFIG = {
    'namespace': os.getenv('NAMESPACE'),
    'scheduler': os.getenv('SCHEDULER', DEF_SCHEDULER_NAME)
}

REQUIRED_FIELDS = ('namespace', 'scheduler')


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
        for event in watcher.stream(client.CoreV1Api().list_namespaced_pod, namespace):
            _type, _pod = event['type'], event['object']
            _name, _phase, _node = _pod.metadata.name, _pod.status.phase, _pod.spec.node_name
            log.debug(f"Received event: {_pod.kind}[{_pod.metadata.name}] {_type} --> {_phase} on node: {_node}")
            if _pod.spec.scheduler_name == scheduler and _phase == "Pending" and _type == 'ADDED':
                try:
                    log.info(f"{_type} {_phase} pod[{_name}] in namespace[{namespace}] "
                             f"with scheduler[{scheduler}] detected!")
                    result = schedule_pod(pod_name=_name, namespace=namespace, method=method)
                    log.debug(f"Received scheduling result: {result}")
                except client.OpenApiException as e:
                    log.error(f"API exception received:\n{e}")
    except KeyboardInterrupt:
        pass
    finally:
        watcher.stop()


def setup_config(params: dict[str, typing.Any]):
    """

    :param params:
    :return:
    """
    CONFIG.update(kv for kv in params.items() if kv[1] is not None)
    if CONFIG.get('namespace') is None and (kube_cfg_ns := pathlib.Path(NS_CONFIG_FILE).resolve(strict=True)).exists():
        CONFIG['namespace'] = kube_cfg_ns.read_text()
    if not all(map(lambda param: bool(CONFIG[param]), REQUIRED_FIELDS)):
        log.error(f"Missing one of the required parameters: {REQUIRED_FIELDS} from {CONFIG}")
        sys.exit(os.EX_CONFIG)
    try:
        config.load_incluster_config()
    except config.ConfigException as e:
        log.error(f"Error loading Kubernetes API config:\n{e}")


def main():
    ################# Parse parameters
    parser = argparse.ArgumentParser(prog=pathlib.Path(__file__).name, description="PTX-edge custom scheduler")
    parser.add_argument("-m", "--method", type=str, default='random',
                        help=f"Applied scheduling method")
    parser.add_argument("-n", "--namespace", type=str, required=False,
                        help="Watched worker namespace")
    parser.add_argument("-s", "--scheduler", type=str, required=False, default=DEF_SCHEDULER_NAME,
                        help="Scheduler name referenced by worker pods")
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
