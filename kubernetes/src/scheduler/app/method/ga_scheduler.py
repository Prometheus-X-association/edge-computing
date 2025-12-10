#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
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
#
# Maintainers:  Peiyuan Guan (peiyuang@ifi.uio.no) Janos Czentye (czentye@tmit.bme.hu)
#
# Genetic Algorithm Scheduler (GA Scheduler)
# Works with Janos' GML format
#
# Requirements:
#    pip install networkx
#
import functools as ft
import itertools as it
import logging
import math
import operator as op
import random as rnd

import networkx as nx

from app.convert import read_topo_from_file, read_pod_from_file, RESOURCES, CAPABILITIES

log = logging.getLogger(__name__)


# -------------------------------------------------------------
#  Constraint checks
# -------------------------------------------------------------
def satisfies_hard_constraints(pod: dict[str, ...], node_attr: dict[str, ...]) -> bool:
    """

    :param pod:
    :param node_attr:
    :return:
    """
    if (not set(pod["zone"]).intersection(node_attr["zone"])
            or (node_attr["pdc"] < pod["collocated"])
            or any(it.starmap(op.lt, ((node_attr["resource"][_r], pod["demand"][_r]) for _r in RESOURCES)))
            or any(it.starmap(op.lt, ((node_attr["capability"][_c], pod["demand"][_c]) for _c in CAPABILITIES)))):
        return False
    else:
        return True


# -------------------------------------------------------------
#  Fitness
# -------------------------------------------------------------
def fitness(pod: dict[str, ...], node_attr: dict[str, ...]) -> float:
    """

    :param node_attr:
    :param pod:
    :return:
    """
    return sum(((node_attr["resource"]["cpu"] - pod["demand"]["cpu"]) / 10,  # More cpu is better despite demand
                (node_attr["resource"]["memory"] - pod["demand"]["memory"]) / 100,  # Memory is hard upper-limited
                (node_attr["resource"]["storage"] - pod["demand"]["storage"]) / 100,  # Storage is hard upper-limited
                int(node_attr["capability"]["gpu"] == pod["prefer"]["gpu"]) * 5,  # Prefer if needed or avoid wasting
                int(node_attr["capability"]["ssd"] == pod["prefer"]["ssd"]) * 3,  # Prefer if needed or avoid wasting
                int(node_attr["pdc"] > pod["collocated"]) * 1), # Prefer collocated PDC for faster communication
               start=0.0)


# -------------------------------------------------------------
#  GA
# -------------------------------------------------------------
def ga_schedule(topology: nx.Graph, pod: dict[str, ...], population_size: int = None, tournament_ratio: float = 1.0,
                pheno_groups: int = 2, generations: int = None, **kwargs) -> str | None:
    """

    :param topology:
    :param pod:
    :param population_size:
    :param tournament_ratio:
    :param pheno_groups:
    :param generations:
    :return:
    """
    nodes = tuple(topology.nodes)
    population_size = population_size if population_size is not None else 2 * len(nodes)
    tournament_size = math.ceil(tournament_ratio * population_size)
    group_size = math.ceil(tournament_size / pheno_groups)
    generations = generations if generations else 3 * len(nodes) + 1

    def evaluate(candidate: str) -> float:
        if candidate is not None and satisfies_hard_constraints(pod, topology.nodes[candidate]):
            return fitness(pod, topology.nodes[candidate])
        else:
            return -math.inf

    def selection(_population: list[str]) -> tuple[list[str], list[float]]:
        _scored = it.islice(sorted(((evaluate(n), n) for n in _population), reverse=True), tournament_size)
        _weights = list(1 / (_j // group_size + 1) for _j in range(tournament_size))
        # population = list(map(op.itemgetter(1), it.islice(it.cycle(_scored), len(_population))))
        return list(map(op.itemgetter(1), _scored)), _weights

    def mutate(candidate: str, _threshold: float = 0.2) -> str:
        return rnd.choice(nodes) if rnd.random() < _threshold else candidate

    def crossover(_candidate1: str, _candidate2: str) -> str:
        return _candidate1 if rnd.random() < 0.5 else _candidate2

    log.debug("Start iterating generations...")
    fittest, population = (-math.inf, None), rnd.choices(nodes, k=population_size)

    for i in range(generations):
        parents, selection_weights = selection(population)
        population = [mutate(crossover(*rnd.choices(parents, weights=selection_weights, k=2)))
                      for _ in range(population_size)]
        best_candidate = ft.reduce(ft.partial(max, key=evaluate), population, initial=None)
        if best_candidate is not None and (best_score := evaluate(best_candidate)) > fittest[0]:
            log.debug(f"New best candidate found in generation {i}/{generations}: {best_candidate}")
            fittest = best_score, best_candidate

    return fittest[1]


# -------------------------------------------------------------
#  K8s Custom scheduler Wrapper
# -------------------------------------------------------------
def do_ga_pod_schedule(topo: nx.Graph, pod: nx.Graph, **params) -> str | None:
    """

    :param topo:
    :param pod:
    :return:
    """
    if len(topo) < 1:
        log.warning(f"No candidate node found in topology: {topo}")
        return None
    log.debug("Extract topo/pod info...")
    def_container = pod.nodes[list(pod.nodes).pop()]
    log.debug("Apply GA node selection...")
    best_node_id = ga_schedule(topology=topo, pod=def_container, **params)
    log.debug(f"Best fit node ID: {best_node_id}")
    return best_node_id


# -------------------------------------------------------------
#  Test
# -------------------------------------------------------------
def test_ga_offline(topo_file: str, pod_file: str):
    topo_data = read_topo_from_file(topo_file)
    pod = read_pod_from_file(pod_file)
    pod_data = pod.nodes[list(pod.nodes)[0]]
    best_node = ga_schedule(topo_data, pod_data)

    node_name = topo_data.nodes[best_node]["metadata"]["name"]
    print("Selected node:", node_name)


# -------------------------------------------------------------
#  Main
# -------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    test_ga_offline("../../resources/example_input_topology.gml", "../../resources/example_input_pod.gml")
    test_ga_offline("../../resources/example_k3s_topology.gml", "../../resources/example_k3s_pod.gml")
