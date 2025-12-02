#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Genetic Algorithm Scheduler (GA Scheduler)
# Works with Janos' GML format
#
# Requirements:
#    pip install networkx
#
import itertools
import logging
import math
import operator
import random

import networkx as nx

log = logging.getLogger(__name__)


# -------------------------------------------------------------
#  Helpers
# -------------------------------------------------------------
def read_topology(filename: str = "input_topology.gml") -> nx.Graph:
    """

    :param filename:
    :return:
    """
    topo = nx.read_gml(filename)
    for node in topo:
        topo.nodes[node]["pdc"] = bool(topo.nodes[node]["pdc"])
        for attr in ('zone', 'capability'):
            for k, v in topo.nodes[node][attr].items():
                topo.nodes[node][attr][k] = bool(v)
    return topo


def read_pod(filename: str = "input_pod.gml") -> dict[str, ...]:
    """

    :param filename:
    :return:
    """
    g = nx.read_gml(filename)
    pod = g.nodes[list(g.nodes)[0]]
    pod['collocated'] = bool(pod['collocated'])
    for attr in ('demand', 'prefer', 'zone'):
        for k, v in pod[attr].items():
            pod[attr][k] = bool(v)
    return pod


# -------------------------------------------------------------
#  Constraint checks
# -------------------------------------------------------------
def satisfies_hard_constraints(pod: dict[str, ...], node_attr: dict[str, ...]) -> bool:
    """

    :param pod:
    :param node_attr:
    :return:
    """
    if (not set(pod["zone"]).intersection(z for z, v in node_attr["zone"].items() if v is True)
            or (pod["collocated"] and not node_attr["pdc"])
            or node_attr["resource"]["cpu"] < pod["demand"]["cpu"]
            or node_attr["resource"]["memory"] < pod["demand"]["memory"]
            or node_attr["resource"]["storage"] < pod["demand"]["storage"]
            or (pod["demand"]["gpu"] and not node_attr["capability"]["gpu"])
            or (pod["demand"]["ssd"] and not node_attr["capability"]["ssd"])):
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
    fit = 0.0
    fit += (node_attr["resource"]["cpu"] - pod["demand"]["cpu"]) / 10
    fit += (node_attr["resource"]["memory"] - pod["demand"]["memory"]) / 100
    fit += (node_attr["resource"]["storage"] - pod["demand"]["storage"]) / 100
    if pod["prefer"]["gpu"] and node_attr["capability"]["gpu"]:
        fit += 5
    if pod["prefer"]["ssd"] and node_attr["capability"]["ssd"]:
        fit += 3
    if not pod["collocated"] and node_attr["pdc"]:
        fit += 1
    return fit


# -------------------------------------------------------------
#  GA
# -------------------------------------------------------------
def ga_schedule(topology: nx.Graph, pod: dict[str, ...], population_size: int = 10,
                generations: int = 20) -> str | None:
    """

    :param topology:
    :param pod:
    :param population_size:
    :param generations:
    :return:
    """
    nodes = tuple(topology.nodes)

    def evaluate(candidate: str) -> float:
        if candidate is not None and satisfies_hard_constraints(pod, topology.nodes[candidate]):
            return fitness(pod, topology.nodes[candidate])
        else:
            return -math.inf

    def selection(_population: list[str]) -> list[str]:
        # scored = []
        # for n in population:
        #     node_attr = topology.nodes[n]
        #     if not satisfies_hard_constraints(pod, node_attr):
        #         scored.append((n, -math.inf))
        #     else:
        #         scored.append((n, fitness(node_attr, pod)))
        # scored.sort(lambda x: x[1], reverse=True)
        scored = sorted([(evaluate(n), n) for n in _population], reverse=True)
        # population = [scored[i % len(scored)][0] for i in range(population_size)]
        return list(map(operator.itemgetter(1), itertools.islice(itertools.cycle(scored), population_size)))

    def mutate(candidate: str) -> str:
        return random.choice(nodes) if random.random() < 0.3 else candidate

    def crossover(_candidate1: str, _candidate2: str) -> str:
        return _candidate1 if random.random() < 0.5 else _candidate2

    log.debug("Start iterating generations...")
    # population = [random.choice(nodes) for _ in range(population_size)]
    fittest, population = (-math.inf, None), random.choices(nodes, k=population_size)

    for i in range(generations):
        # new_pop = []
        # for i in range(population_size):
        #     p1 = random.choice(population)
        #     p2 = random.choice(population)
        #     child = crossover(p1, p2)
        #     child = mutate(child)
        #     new_pop.append(child)
        # population = new_pop
        population = [mutate(crossover(*random.choices(selection(population), k=2))) for _ in range(population_size)]
        # best, best_score = None, -math.inf
        # for n in population:
        #     node_attr = topology.nodes[n]
        #     s = fitness(node_attr, pod) if satisfies_hard_constraints(pod, node_attr) else -math.inf
        #     if s > best_score:
        #         best, best_score = n, s
        # best = functools.reduce(functools.partial(max, key=evaluate), population, initial=None)
        best = max(zip(map(evaluate, population), population))
        if best[0] > fittest[0]:
            log.debug(f"New best candidate found in generation {i}: {best[1]}")
            fittest = best

    return fittest[1]


# -------------------------------------------------------------
#  K8s Custom scheduler Wrapper
# -------------------------------------------------------------
def do_ga_pod_schedule(topo: nx.Graph, pod: nx.Graph, **params) -> str:
    """

    :param topo:
    :param pod:
    :return:
    """
    log.debug("Extract topo/pod info...")
    def_container = pod.nodes[list(pod.nodes).pop()]
    log.debug("Execute ga_schedule algorithm...")
    best_node_id = ga_schedule(topology=topo, pod=def_container, **params)
    log.debug(f"Best fit node ID: {best_node_id}")
    return best_node_id


# -------------------------------------------------------------
#  Test
# -------------------------------------------------------------
def test_ga_offline(topo_file: str, pod_file: str):
    topo_data = read_topology(topo_file)
    pod_data = read_pod(pod_file)
    best_node = ga_schedule(topo_data, pod_data)

    node_name = topo_data.nodes[best_node]["metadata"]["name"]
    print("Selected node:", node_name)

    # with open("../../resources/output.txt", "w") as f:
    #     f.write(node_name)


# -------------------------------------------------------------
#  Main
# -------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    test_ga_offline("../../resources/example_input_topology.gml", "../../resources/example_input_pod.gml")
    test_ga_offline("../../resources/example_k3s_topology.gml", "../../resources/example_k3s_pod.gml")
