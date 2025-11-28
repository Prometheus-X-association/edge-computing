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
import random
import typing
from itertools import starmap
from operator import le

import networkx as nx

log = logging.getLogger(__name__)

RESOURCES = ('cpu', 'memory', 'storage')
CAPABILITIES = ('ssd', 'gpu')


def _filter_nodes(topo: nx.Graph, pod: nx.Graph) -> typing.Generator[str, None, None]:
    """

    :param topo:
    :param pod:
    :return:
    """
    log.debug(f"Calculated pod[{pod.name}] info:")
    pod_zones = set(z for _c in pod for z, v in pod.nodes[_c]['zone'].items() if v)
    log.debug(f"\t- zones: {pod_zones}")
    pod_res = list(map(sum, (map(lambda c: pod.nodes[c]['demand'][_r], pod.nodes) for _r in RESOURCES)))
    log.debug(f"\t- resources: {dict(zip(RESOURCES, pod_res))}")
    pod_cap = list(map(all, (map(lambda c: pod.nodes[c]['demand'][_c], pod.nodes) for _c in CAPABILITIES)))
    log.debug(f"\t- capabilities: {dict(zip(CAPABILITIES, pod_cap))}")
    log.info(f"Filtering nodes from {topo.name}...")
    for node, ndata in topo.nodes(data=True):
        log.debug(f"Collected node[{node}] info:")
        node_zone = set(z for z, v in ndata['zone'].items() if v)
        log.debug(f"\t- zones: {node_zone}")
        log.debug(f"\t- resources: {ndata['resource']}")
        log.debug(f"\t- capabilities: {ndata['capability']}")
        if (pod_zones & node_zone
                and all(starmap(le, zip(pod_res, (ndata['resource'][_r] for _r in RESOURCES))))
                and all(starmap(le, zip(pod_cap, (ndata['capability'][_r] for _r in CAPABILITIES))))):
            log.info(f">>> Feasible node found: {node}")
            yield node


def random_schedule(nodes: list[str]) -> str:
    """

    :param nodes:
    :return:
    """
    return random.choice(nodes)


def do_random_pod_schedule(topo: nx.Graph, pod: nx.Graph) -> str:
    """

    :param topo:
    :param pod:
    :return:
    """
    filtered_node_list = list(_filter_nodes(topo=topo, pod=pod))
    log.debug(f"Filtered nodes: {filtered_node_list}")
    log.debug("Apply random node selection...")
    selected_node = random_schedule(nodes=filtered_node_list)
    return selected_node
