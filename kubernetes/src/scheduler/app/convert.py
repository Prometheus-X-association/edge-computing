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
import logging

import networkx as nx
from kubernetes import client

from app.k8s import get_available_nodes, get_pods_by_node
from app.utils import str2bool, cpu2int, bits2int

log = logging.getLogger(__name__)

LABEL_PDC_ENABLED = 'connector.dataspace.ptx.org/enabled'
LABEL_PZ_PREFIX = 'privacy-zone.dataspace.ptx.org/'
LABEL_DISK_PREFIX = "disktype"
LABEL_GPU_SUPPORT = "accelerator/gpu"
DEF_PZ = "default"


def __create_pod_data(pod: client.V1Pod) -> dict[str, ...]:
    pod_data = {
        'priority': int(pod.spec.priority),
        'demand': {
            'cpu': sum(cpu2int(c.resources.requests.get('cpu', 0))
                       for c in pod.spec.containers if c.resources and c.resources.requests),
            'memory': sum(bits2int(c.resources.requests.get('memory', 0))
                          for c in pod.spec.containers if c.resources and c.resources.requests),
            'storage': 0,  # Not supported directly in K8s
            'ssd': pod.spec.node_selector.get(LABEL_DISK_PREFIX) == 'ssd' if pod.spec.node_selector else False,
            'gpu': str2bool(pod.spec.node_selector.get(LABEL_GPU_SUPPORT) if pod.spec.node_selector else False)
        },
        'prefer': {
            'cpu': sum(cpu2int(c.resources.limits.get('cpu', 0))
                       for c in pod.spec.containers if c.resources and c.resources.limits),
            'memory': sum(bits2int(c.resources.limits.get('memory', 0))
                          for c in pod.spec.containers if c.resources and c.resources.limits),
            'storage': 0,  # Not supported directly in K8s
            'ssd': pod.metadata.annotations.get(LABEL_DISK_PREFIX) == 'ssd' if pod.metadata.annotations else False,
            'gpu': str2bool(pod.metadata.annotations.get(LABEL_GPU_SUPPORT) if pod.metadata.annotations else False)
        },
        'zone': ",".join(s.removeprefix(LABEL_PZ_PREFIX) for s, v in pod.spec.node_selector.items()
                         if s.startswith(LABEL_PZ_PREFIX) and str2bool(v)) if pod.spec.node_selector else DEF_PZ,
        'collocated': str2bool(pod.spec.node_selector.get(LABEL_PDC_ENABLED)) if pod.spec.node_selector else False,
        'metadata': {
            'name': pod.metadata.name,
            'namespace': pod.metadata.namespace,
            'created': pod.metadata.creation_timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
            'scheduler': pod.spec.scheduler_name,
            'status': pod.status.phase,
            'labels': pod.metadata.labels.copy(),
        }
    }
    # TODO - check PZ in affinity rules
    return pod_data


def convert_pod_to_nx(pod: client.V1Pod) -> nx.Graph:
    pod_obj = nx.Graph(name='Pod')
    pod_obj.add_node(pod.metadata.name, **__create_pod_data(pod=pod))
    return pod_obj


def convert_topo_to_nx(ns: str) -> nx.Graph:
    topo_obj = nx.Graph(name='Topology')
    for i, node in enumerate(get_available_nodes(), start=1):
        node_data = {
            'resources': {
                'cpu': int(cpu2int(node.status.allocatable['cpu']) * 1e3),
                'memory': bits2int(node.status.allocatable.get('memory', 0)),
                'storage': bits2int(node.status.allocatable.get('ephemeral-storage', 0))
            },
            'zones': dict.fromkeys((DEF_PZ, *(l.removeprefix(LABEL_PZ_PREFIX)
                                              for l, v in node.metadata.labels.items()
                                              if l.startswith(LABEL_PZ_PREFIX) and str2bool(v))), True),
            'pdc': str2bool(node.metadata.labels.get(LABEL_PDC_ENABLED)),
            'capability': {
                "ssd": node.metadata.labels.get(LABEL_DISK_PREFIX) == 'ssd',
                "gpu": str2bool(node.metadata.labels.get(LABEL_GPU_SUPPORT)),
            },
            'pods': {p.metadata.name: convert_pod_to_nx(p).nodes[p.metadata.name]
                     for p in get_pods_by_node(node=node.metadata.name, ns=ns)},
            'metadata': {
                'name': node.metadata.name,
                'architecture': node.status.node_info.architecture,
                'os': node.status.node_info.operating_system,
                'kernel': node.status.node_info.kernel_version,
                'ip': ",".join(a.address for a in node.status.addresses if a.type == 'InternalIP')
            }
        }
        topo_obj.add_node(node.metadata.name, **node_data)
    return topo_obj
