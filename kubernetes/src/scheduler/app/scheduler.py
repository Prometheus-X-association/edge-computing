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

import networkx as nx
from kubernetes import client, watch

from app import __version__
from app.config import setup_config, CONFIG, DEF_SCHEDULER_METHOD, DEF_SCHEDULER_NAME
from app.k8s import assign_pod_to_node, create_failed_scheduling_event, get_available_nodes
from app.method.ga_scheduler import ga_schedule
from app.method.random_scheduler import random_schedule
from app.utils import setup_logging, nx_graph_to_str

log = logging.getLogger(__name__)

LABEL_PDC_ENABLED = 'connector.dataspace.ptx.org/enabled'
LABEL_PZ_PREFIX = 'privacy-zone.dataspace.ptx.org'
LABEL_DISK_PREFIX = "disktype"
LABEL_GPU_ENABLED = "accelerator/gpu"


def create_topology_description() -> nx.Graph:
    topo_obj = nx.Graph(name='topology')
    for i, node in enumerate(get_available_nodes(), start=1):
        node_data = {
            'metadata': {
                'name': node.metadata.name,
                'architecture': node.status.node_info.architecture,
                'os': node.status.node_info.operating_system,
                'kernel': node.status.node_info.kernel_version,
                'ip': ",".join(a.address for a in node.status.addresses if a.type == 'InternalIP')
            },

        }
        topo_obj.add_node(f"node_{i}", **node_data)
    return topo_obj


def create_pod_description(pod: client.V1Pod) -> nx.Graph:
    pod_obj = nx.Graph(name='pod')
    pod_obj.add_node(pod.metadata.name, metadata={'name': pod.metadata.name})
    return pod_obj


def schedule_pod(pod: client.V1Pod) -> str:
    """

    :param pod:
    :return:
    """
    pod_name = pod.metadata.name
    log.info(f"Scheduling pod[{pod_name}] in namespace: {CONFIG['namespace']} using method: {CONFIG['method']}...")
    topo = create_topology_description()
    log.info(f"Collected topology info: {topo}")
    log.debug(nx_graph_to_str(topo))
    pod = create_pod_description(pod=pod)
    log.info(f"Collected Pod info: {pod}")
    log.debug(nx_graph_to_str(pod))
    node_id = None
    match CONFIG['method']:
        case 'random':
            log.info("Initiate RANDOM node selection")
            log.debug("Apply random node selection...")
            node_id = random_schedule(topo=topo, pod=pod)
            log.debug(f"Chosen node ID: {node_id}")
        case 'genetic':
            log.info("Initiate GA node selection")
            log.debug("Execute ga_schedule algorithm...")
            node_id = ga_schedule(topology=topo, pod=pod)
            log.debug(f"Best fit node ID: {node_id}")
        case _:
            log.error(f"Unknown scheduler method: {CONFIG['method']}")
            sys.exit(os.EX_USAGE)
    if node_id is not None:
        selected_node = str(topo.nodes[node_id]["metadata"]["name"])
        log.info(f"Selected node name: {selected_node}")
        ret = assign_pod_to_node(pod_name=pod_name, node_name=selected_node)
        return "Success" if ret is not None else "Failed"
    else:
        log.error("Missing selected node!")
        create_failed_scheduling_event(pod_name=pod_name)
        return "Failed"


def serve_forever(**kwargs):
    """

    :param kwargs:
    :return:
    """
    log.info(f"Scheduler[{CONFIG['scheduler']}] is listening on namespace: {CONFIG['namespace']}...")
    while True:
        watcher = watch.Watch()
        log.debug("Waiting for events...")
        try:
            for event in watcher.stream(client.CoreV1Api().list_namespaced_pod, namespace=CONFIG['namespace'],
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
                result = schedule_pod(pod=_pod)
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
