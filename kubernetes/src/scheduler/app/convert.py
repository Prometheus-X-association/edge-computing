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
import copy
import logging
import pathlib

import networkx as nx
from kubernetes import client

from app.k8s import get_available_nodes, get_pods_by_node
from app.utils import str2bool, cpu2int, bits2int

log = logging.getLogger(__name__)

LABEL_PDC_ENABLED = 'connector.dataspace.ptx.org/enabled'
LABEL_PZ_PREFIX = 'privacy-zone.dataspace.ptx.org/'
LABEL_DISK_PREFIX = "hardware/disktype"
LABEL_GPU_SUPPORT = "accelerator/gpu"
DEF_PZ = "default"

RESOURCES = ('cpu', 'memory', 'storage')
CAPABILITIES = ('ssd', 'gpu')


def __create_pod_data(pod: client.V1Pod) -> dict[str, ...]:
    """

    :param pod:
    :return:
    """
    pod_data = {
        'priority': int(pod.spec.priority),
        'demand': {
            'cpu': sum(cpu2int(c.resources.requests.get('cpu', 0))
                       for c in pod.spec.containers if c.resources and c.resources.requests),
            'memory': sum(bits2int(c.resources.requests.get('memory', 0))
                          for c in pod.spec.containers if c.resources and c.resources.requests),
            'storage': 0,  # Not supported directly in K8s
            # TODO - EmptyDir(default) counts from ephemeral storage, EmptyDir("Memory") allocates memory (tmpfs)
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
        'zone': list(s.removeprefix(LABEL_PZ_PREFIX) for s, v in pod.spec.node_selector.items()
                     if s.startswith(LABEL_PZ_PREFIX) and str2bool(v)) if pod.spec.node_selector else [DEF_PZ],
        'collocated': str2bool(pod.spec.node_selector.get(LABEL_PDC_ENABLED)) if pod.spec.node_selector else False,
        'metadata': {
            'api_version': "v1",
            'kind': "Pod",
            'name': pod.metadata.name,
            'namespace': pod.metadata.namespace,
            'resource_version': pod.metadata.resource_version,
            'uid': pod.metadata.uid,
            'labels': copy.deepcopy(pod.metadata.labels),
            'info': {
                'creation_timestamp': pod.metadata.creation_timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
                'node': pod.spec.node_name,
                'scheduler': pod.spec.scheduler_name,
                'status': pod.status.phase,
                'ip': pod.status.pod_ip
            }
        }
    }
    if pod.spec.affinity and pod.spec.affinity.node_affinity:
        if ((reqs := pod.spec.affinity.node_affinity.required_during_scheduling_ignored_during_execution)
                and reqs.node_selector_terms):
            # Default scheduler OR the different terms, here it is ANDed!
            for term in reqs.node_selector_terms:
                if term.match_expressions:
                    for ex in term.match_expressions:
                        if ex.key.startswith(LABEL_PZ_PREFIX) and ex.operator == 'In' and str2bool(ex.values[0]):
                            if (zone := ex.key.removeprefix(LABEL_PZ_PREFIX)) not in pod_data['zone']:
                                pod_data['zone'].append(zone)
                        elif ex.key == LABEL_PDC_ENABLED and ex.operator == 'In' and str2bool(ex.values[0]):
                            pod_data['collocated'] = True
                        elif ex.key == LABEL_DISK_PREFIX and ex.operator == 'In' and 'SSD' in map(str.upper, ex.values):
                            pod_data['demand']['ssd'] = True
                        elif ex.key == LABEL_GPU_SUPPORT and ex.operator == 'In' and str2bool(ex.values[0]):
                            pod_data['demand']['gpu'] = True
        if prefs := pod.spec.affinity.node_affinity.preferred_during_scheduling_ignored_during_execution:
            for pref in prefs:
                if pref.preference.match_expressions:
                    for ex in pref.preference.match_expressions:
                        if ex.key == LABEL_DISK_PREFIX and ex.operator == 'In' and 'SSD' in map(str.upper, ex.values):
                            pod_data['prefer']['ssd'] = True
                        elif ex.key == LABEL_GPU_SUPPORT and ex.operator == 'In' and str2bool(ex.values[0]):
                            pod_data['prefer']['gpu'] = True
    # TODO - also consider affinity rules in pod's PVC node affinity
    return pod_data


def convert_pod_to_nx(pod: client.V1Pod) -> nx.Graph:
    """

    :param pod:
    :return:
    """
    pod_obj = nx.Graph(name='Pod')
    pod_obj.add_node(pod.metadata.name, **__create_pod_data(pod=pod))
    return pod_obj


def __post_process_topo(topo_obj: nx.Graph) -> nx.Graph:
    """

    :param topo_obj:
    :return:
    """
    for node in topo_obj:
        nres = copy.deepcopy(topo_obj.nodes[node]['capacity'])
        for pod, pdata in topo_obj.nodes[node]['pod'].items():
            for r in RESOURCES:
                nres[r] = max(0, nres.get(r, 0) - max(pdata['demand'].get(r, 0), pdata['prefer'].get(r, 0)))
        topo_obj.nodes[node]['resource'] = nres
    return topo_obj


def convert_topo_to_nx(ns: str) -> nx.Graph:
    """

    :param ns:
    :return:
    """
    topo_obj = nx.Graph(name='Topology')
    for i, node in enumerate(get_available_nodes(), start=1):
        node_data = {
            'resource': {},  # Placeholder for calculating available resources in post process
            'capacity': {
                'cpu': int(cpu2int(node.status.allocatable['cpu']) * 1e3),
                'memory': bits2int(node.status.allocatable.get('memory', 0)),
                'storage': bits2int(node.status.allocatable.get('ephemeral-storage', 0))
            },
            'zone': [DEF_PZ, *(l.removeprefix(LABEL_PZ_PREFIX) for l, v in node.metadata.labels.items()
                               if l.startswith(LABEL_PZ_PREFIX))],
            'pdc': str2bool(node.metadata.labels.get(LABEL_PDC_ENABLED)),
            'capability': {
                "ssd": node.metadata.labels.get(LABEL_DISK_PREFIX) == 'ssd',
                "gpu": str2bool(node.metadata.labels.get(LABEL_GPU_SUPPORT)),
            },
            'pod': {p.metadata.name: __create_pod_data(p) for p in get_pods_by_node(node=node.metadata.name, ns=ns)
                    if p.status.phase == "Running"},
            'metadata': {
                'api_version': "v1",
                'kind': "Node",
                'name': node.metadata.name,
                'resource_version': node.metadata.resource_version,
                'uid': node.metadata.uid,
                'info': {
                    'architecture': node.status.node_info.architecture,
                    'os': node.status.node_info.operating_system,
                    'kernel': node.status.node_info.kernel_version,
                    'ip': ",".join(a.address for a in node.status.addresses if a.type == 'InternalIP')
                }
            }
        }
        topo_obj.add_node(node.metadata.name, **node_data)
    # TODO - add links (full mesh?) and link metrics
    __post_process_topo(topo_obj)
    return topo_obj


def __parse_pod_data(pod_data: dict[str, ...]) -> dict[str, ...]:
    pod_data['collocated'] = bool(pod_data['collocated'])
    for const in ('demand', 'prefer'):
        for attr in ('ssd', 'gpu'):
            pod_data[const][attr] = bool(pod_data[const][attr])
    return pod_data


def read_pod_from_file(filename: str | pathlib.Path) -> nx.Graph:
    """

    :param filename:
    :return:
    """
    g = nx.read_gml(filename)
    for _, pod_data in g.nodes.data():
        __parse_pod_data(pod_data)
    return g


def read_topo_from_file(filename: str | pathlib.Path) -> nx.Graph:
    """

    :param filename:
    :return:
    """
    topo = nx.read_gml(filename)
    for node in topo:
        topo.nodes[node]["pdc"] = bool(topo.nodes[node]["pdc"])
        for k, v in topo.nodes[node]['capability'].items():
            topo.nodes[node]['capability'][k] = bool(v)
        for pod in topo.nodes[node]['pod'].values():
            pod['collocated'] = bool(pod['collocated'])
            for const in ('demand', 'prefer'):
                for attr in ('ssd', 'gpu'):
                    pod[const][attr] = bool(pod[const][attr])
    return topo
