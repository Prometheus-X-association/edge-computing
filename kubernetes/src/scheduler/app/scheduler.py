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

from kubernetes import client, watch

from app import __version__
from app.config import CONFIG, DEF_SCHEDULER_METHOD, DEF_SCHEDULER_NAME, setup_config, param_parser
from app.convert import convert_topo_to_nx, convert_pod_to_nx
from app.k8s import assign_pod_to_node, raise_failed_k8s_scheduling_event
from app.method.ga_scheduler import do_ga_pod_schedule
from app.method.random_scheduler import do_random_pod_schedule
from app.utils import setup_logging, nx_graph_to_str

log = logging.getLogger(__name__)


def schedule_pod(pod: client.V1Pod, params: dict[str, ...]) -> str:
    """

    :param pod:
    :param params:
    :return:
    """
    log.info(f"Scheduling pod[{pod.metadata.name}] in namespace: {CONFIG['namespace']} with method: {CONFIG['method']}")
    topo_nx = convert_topo_to_nx(ns=pod.metadata.namespace)
    log.info(f"Collected topology info: {topo_nx}")
    log.debug(f"{topo_nx.name}:\n{nx_graph_to_str(topo_nx)}")
    pod_nx = convert_pod_to_nx(pod=pod)
    log.info(f"Collected Pod info: {pod_nx}")
    log.debug(f"{pod_nx.name}:\n{nx_graph_to_str(pod_nx)}")
    node_id = None
    match CONFIG['method']:
        case 'random':
            log.info("Initiate <RANDOM> node selection")
            node_id = do_random_pod_schedule(topo=topo_nx, pod=pod_nx, **params)
        case 'genetic':
            log.info("Initiate <GA> node selection")
            node_id = do_ga_pod_schedule(topo=topo_nx, pod=pod_nx, **params)
        case 'linear':
            raise NotImplementedError
        case _:
            log.error(f"Unknown scheduler method: {CONFIG['method']}")
            sys.exit(os.EX_USAGE)
    if node_id is None:
        log.error(f"No feasible node is found by strategy: {CONFIG['method']}!")
        raise_failed_k8s_scheduling_event(pod=pod,
                                          ns=CONFIG['namespace'],
                                          scheduler=CONFIG['scheduler'],
                                          method=CONFIG['method'],
                                          reason=f"0/{len(topo_nx)} nodes match Pod's node affinity/selector.")
        return "Failed"
    else:
        selected_node_name = str(topo_nx.nodes[node_id]["metadata"]["name"])
        log.info(f"Selected node name: {selected_node_name}")
        ret = assign_pod_to_node(pod=pod,
                                 ns=CONFIG['namespace'],
                                 node_meta=topo_nx.nodes[node_id]['metadata'],
                                 scheduler=CONFIG['scheduler'],
                                 method=CONFIG['method'])
        return "Success" if ret is not None else "Failed"


def serve_forever(params: dict[str, ...]):
    """

    :param params:
    :return:
    """
    log.info(f"Scheduler[{CONFIG['scheduler']}] is listening on namespace: {CONFIG['namespace']}")
    while True:
        watcher = watch.Watch()
        log.debug("Waiting for events...")
        try:
            for event in watcher.stream(client.CoreV1Api().list_namespaced_pod,
                                        namespace=CONFIG['namespace'],
                                        field_selector=f"spec.schedulerName={CONFIG['scheduler']},"
                                                       f"status.phase=Pending"):
                _type, _pod = event['type'], event['object']
                _name = _pod.metadata.name
                log.debug(f"Received event: {_pod.kind}[{_name}] {_type} --> "
                          f"{_pod.status.phase} on node: {_pod.spec.node_name}")
                if _type != 'ADDED':
                    continue
                log.info(f"{_type} pod[{_name}] in namespace[{CONFIG['namespace']}] "
                         f"with scheduler[{CONFIG['scheduler']}] detected!")
                result = schedule_pod(pod=_pod, params=params)
                log.debug(f"Received scheduling result: {result}")
        except KeyboardInterrupt:
            log.info("KeyboardInterrupt received. Stopping scheduler...")
            break
        except client.ApiException as e:
            log.debug(f"API exception received:\n{e}")
            if e.status == 410:
                log.debug("Restart watcher....")
                continue
            else:
                break
        finally:
            watcher.stop()
            log.debug("Stop watching for pod scheduling events")


def main():
    ################# Parse parameters
    parser = argparse.ArgumentParser(prog=pathlib.Path(__file__).name, description="PTX-edge custom scheduler")
    parser.add_argument("-m", "--method", type=str, default=DEF_SCHEDULER_METHOD,
                        help=f"Applied scheduling method (def: {DEF_SCHEDULER_METHOD})")
    parser.add_argument("-n", "--namespace", type=str, required=False,
                        help="Watched worker namespace (def: from kube cfg/envvar)")
    parser.add_argument("-s", "--scheduler", type=str, required=False, default=DEF_SCHEDULER_NAME,
                        help=f"Scheduler name referenced by worker pods (def: {DEF_SCHEDULER_NAME})")
    parser.add_argument("-p", "--parameters", type=str, required=False,
                        help="Comma-separated additional parameters for scheduling algorithm")
    parser.add_argument("-v", "--verbose", action='count', default=0, required=False,
                        help="Increase verbosity")
    parser.add_argument("-V", "--version", action='version', version=f"{parser.description} v{__version__}")
    args = parser.parse_args()
    ################# Setup configuration
    setup_logging(verbosity=args.verbose)
    setup_config(params=vars(args))
    params = param_parser(params=args.parameters)
    ################# Handle scheduling events
    try:
        serve_forever(params=params)
    except Exception as e:
        log.error(f"Unexpected error received:\n{e}")
        log.exception(e)
        sys.exit(os.EX_SOFTWARE)


if __name__ == '__main__':
    main()
