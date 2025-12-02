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

from app.convert import read_topo_from_file, read_pod_from_file, RESOURCES, CAPABILITIES

log = logging.getLogger(__name__)


def _filter_nodes(topo: nx.Graph, pod: nx.Graph) -> typing.Generator[str, None, None]:
    """

    :param topo:
    :param pod:
    :return:
    """
    log.debug(f"Calculated pod[{pod.name}] info:")
    pod_zones = set(z for _c in pod for z in pod.nodes[_c]['zone'])
    log.debug(f"\t- zones: {pod_zones}")
    pod_res = list(map(sum, (map(lambda c: pod.nodes[c]['demand'][_r], pod.nodes) for _r in RESOURCES)))
    log.debug(f"\t- resources: {dict(zip(RESOURCES, pod_res))}")
    pod_cap = list(map(all, (map(lambda c: pod.nodes[c]['demand'][_c], pod.nodes) for _c in CAPABILITIES)))
    log.debug(f"\t- capabilities: {dict(zip(CAPABILITIES, pod_cap))}")
    log.info(f"Filtering nodes from {topo.name}...")
    for node, ndata in topo.nodes(data=True):
        log.debug(f"Collected node[{node}] info:")
        node_zone = set(ndata['zone'])
        log.debug(f"\t- zones: {node_zone}")
        log.debug(f"\t- resources: {ndata['resource']}")
        log.debug(f"\t- capabilities: {ndata['capability']}")
        if (pod_zones & node_zone
                and all(starmap(le, zip(pod_res, (ndata['resource'][_r] for _r in RESOURCES))))
                and all(starmap(le, zip(pod_cap, (ndata['capability'][_r] for _r in CAPABILITIES))))):
            log.info(f">>> Feasible node found: {node}")
            yield node


def random_schedule(nodes: list[str]) -> str | None:
    """

    :param nodes:
    :return:
    """
    try:
        return random.choice(nodes)
    except IndexError:
        return None


def do_random_pod_schedule(topo: nx.Graph, pod: nx.Graph, **params) -> str | None:
    """

    :param topo:
    :param pod:
    :return:
    """
    filtered_node_list = list(_filter_nodes(topo=topo, pod=pod))
    log.debug(f"Filtered nodes: {filtered_node_list}")
    log.debug("Apply random node selection...")
    if 'seed' in params:
        random.seed(params['seed'])
    selected_node = random_schedule(nodes=filtered_node_list)
    log.debug(f"Selected node ID: {selected_node}")
    return selected_node


########################################################################################################################

def test_random_offline(topo_file: str, pod_file: str):
    topo_data = read_topo_from_file(topo_file)
    pod_data = read_pod_from_file(pod_file)
    best_node = do_random_pod_schedule(topo_data, pod_data)

    node_name = topo_data.nodes[best_node]["metadata"]["name"]
    print("Selected node:", node_name)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    test_random_offline("../../resources/example_input_topology.gml", "../../resources/example_input_pod.gml")
    test_random_offline("../../resources/example_k3s_topology.gml", "../../resources/example_k3s_pod.gml")
