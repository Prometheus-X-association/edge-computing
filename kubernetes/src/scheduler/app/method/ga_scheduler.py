#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Genetic Algorithm Scheduler (GA Scheduler)
# Works with Janos' GML format
#
# Requirements:
#    pip install networkx
#
import logging
import random

import networkx as nx

log = logging.getLogger(__name__)


# -------------------------------------------------------------
#  Helpers
# -------------------------------------------------------------
def read_topology(filename="input_topology.gml"):
    topo = nx.read_gml(filename)
    for node in topo:
        topo.nodes[node]["pdc"] = bool(topo.nodes[node]["pdc"])
        for attr in ('zone', 'capability'):
            for k, v in topo.nodes[node][attr].items():
                topo.nodes[node][attr][k] = bool(v)
    return topo


def read_pod(filename="input_pod.gml"):
    g = nx.read_gml(filename)
    pod = g.nodes[list(g.nodes)[0]]
    pod['collocated'] = bool(pod['collocated'])
    for attr in ('demand', 'prefer', 'zone'):
        for k, v in pod[attr].items():
            pod[attr][k] = bool(v)
    return pod


def get_node_name(node_attr):
    return node_attr["metadata"]["name"]


# -------------------------------------------------------------
#  Constraint checks
# -------------------------------------------------------------
def satisfies_hard_constraints(pod, node):
    demand = pod["demand"]
    zone = set(pod["zone"])

    if not zone.intersection(z for z, v in node["zone"].items() if v is True):
        return False
    if pod["collocated"] and node["pdc"] != 1:
        return False
    if node["resource"]["cpu"] < demand["cpu"]:
        return False
    if node["resource"]["memory"] < demand["memory"]:
        return False
    if node["resource"]["storage"] < demand["storage"]:
        return False
    if demand["gpu"] and not node["capability"]["gpu"]:
        return False
    if demand["ssd"] and not node["capability"]["ssd"]:
        return False
    return True


# -------------------------------------------------------------
#  Fitness
# -------------------------------------------------------------
def fitness(node_attr, pod):
    prefer = pod["prefer"]
    demand = pod["demand"]
    fit = 0.0
    fit += (node_attr["resource"]["cpu"] - demand["cpu"]) / 10
    fit += (node_attr["resource"]["memory"] - demand["memory"]) / 100
    fit += (node_attr["resource"]["storage"] - demand["storage"]) / 100
    if prefer["gpu"] and node_attr["capability"]["gpu"]:
        fit += 5
    if prefer["ssd"] and node_attr["capability"]["ssd"]:
        fit += 3
    if not pod["collocated"] and node_attr["pdc"]:
        fit += 1
    return fit


# -------------------------------------------------------------
#  GA
# -------------------------------------------------------------
def ga_schedule(topology, pod, population_size=10, generations=20):
    nodes = list(topology.nodes)

    population = [random.choice(nodes) for _ in range(population_size)]

    def mutate(candidate):
        return random.choice(nodes) if random.random() < 0.3 else candidate

    def crossover(a, b):
        return a if random.random() < 0.5 else b

    for _ in range(generations):
        scored = []
        for n in population:
            node_attr = topology.nodes[n]
            if not satisfies_hard_constraints(pod, node_attr):
                scored.append((n, -9999))
            else:
                scored.append((n, fitness(node_attr, pod)))
        scored.sort(key=lambda x: x[1], reverse=True)
        population = [scored[i % len(scored)][0] for i in range(population_size)]

        new_pop = []
        for i in range(population_size):
            p1 = random.choice(population)
            p2 = random.choice(population)
            child = crossover(p1, p2)
            child = mutate(child)
            new_pop.append(child)
        population = new_pop

    best = None
    best_score = -1e9
    for n in population:
        node_attr = topology.nodes[n]
        if satisfies_hard_constraints(pod, node_attr):
            s = fitness(node_attr, pod)
        else:
            s = -9999
        if s > best_score:
            best_score = s
            best = n

    return best


# -------------------------------------------------------------
#  K8s Custom scheduler Wrapper
# -------------------------------------------------------------
def do_ga_pod_schedule(topo: nx.Graph, pod: nx.Graph) -> str:
    """

    :param topo:
    :param pod:
    :return:
    """
    log.debug("Extract topo/pod info...")
    def_container = pod.nodes[list(pod.nodes).pop()]
    log.debug("Execute ga_schedule algorithm...")
    best_node_id = ga_schedule(topology=topo, pod=def_container)
    return best_node_id


# -------------------------------------------------------------
#  Main
# -------------------------------------------------------------
if __name__ == "__main__":
    topo = read_topology("../../resources/example_input_topology.gml")
    pod = read_pod("../../resources/example_input_pod.gml")
    best_node = ga_schedule(topo, pod)

    node_name = topo.nodes[best_node]["metadata"]["name"]
    print("Selected node:", node_name)

    # with open("output.txt", "w") as f:
    #     f.write(node_name)
