#!/usr/bin/env python3
# Copyright 2023 Janos Czentye
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

import networkx as nx  # python3 -m pip install networkx

# Since we want dataspace-related scheduling (originally planned to be situated in edge-cloud environments),
# I think modeling the topology as an undirected graph will be useful. Initially, I propose the following formats:
#
# Input (twofold):
#   Topology graph:
#       node: represent a physical node
#           Parameters:
#               "cpu" (available cpu cores),
#               "memory" (available/free memory),
#               "zones" (list of privacy zone ID(s) the node belongs to)
#               "pdc": (a flag/bool marking that the node is dedicated to run a dataspace connector (PDC),
#                               where the collected private data is stored and each deployed pod must communicate with
#                               other dataspace participant via this PDC)
#           optionally:
#               "pods" (the pods/containers that have already been scheduled/running on the nodes with their parameters)
#               "storage" ephemeral storage size,
#               "ssd", "gpu": flags marking the node has SSD drive/GPU acceleration
#       edge: represent a network link between physical nodes
#           Parameters:
#               "delay" (expected/measured delay between nodes),
#               "bw" (expected bandwidth/capacity of the network connection)
#           optionally: other network characteristics that can be measured somehow...
#
#     Pod/container meant to be deployed
#         Requested (minimum) "cpu" demand and/or maximum/preferred "cpu" limit
#         Requested (minimum) "memory" demand and/or maximum/preferred "mem" limit
#         "zone": the privacy zone ID that is demanded to be deployed into
#         "collocated": a flag marking that the pod/container is deployed with "near-data processing",
#               i.e., must be collocated with a PDC that belongs to the demanded privacy zone ("zone")
#         optionally:
#           "storage" ephemeral storage demands,
#           "ssd" and "gpu" with 3 states: "no", "preferred", "demanded".
#               These two can be also modeled as requested and preferred constraints, just like cpu, mem, and storage.
#
# Output (single):
#  the "node" ID to which the given pod is assigned
#
# As a reminder, in Privacy Preserving mode we want to deploy a pod in its requested privacy zone, and preferably close
# to the zone's pdc to reduce communication overhead/privacy concerns. In general, pods can be assigned to nodes, where
# sufficient resources (cpu, mem, storage) are available and belongs to the privacy zone demand (hard constraint).
# SSD and GPU acceleration options can be formulated as preferred features (soft constraints) or demanded requirements
# (hard constraints). Currently, there is no option to define delay/bw constraint to a pod, so these parameters can be
# leveraged, e.g., to evenly distribute pods in a privacy zone to keep network link load (bw) low.
# Pod resources defines basically and interval between the demand and prefer values. Resource requests are hard
# constraints, and pods' resource usage can grow until their limits, at which Kubernetes evicts pods. So resource
# limits can be considered as soft constraints, good to have enough resource up to their limits, but pods are
# operational on requested resources.
# More on the topic: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/
#
# In Near-data Processing mode, pods must be collocated with a PDC to manage private data transmission between the PDC's
# database and the worker pod (node)-locally for increased privacy. In this case, that is another hard constrain.
# Finally, a privacy zone usually consists of multiple nodes and one node can belong to multiple zones, as well as,
# a pdc-enabled node belonging to multiple zones can run a PDC that serves out that privacy zones simultaneously.
#
# Moreover, I only consider the "node resources", "pdc", and "collocated" parameters mandatory and always to be
# provided, others are optional and filled with default values. Thus, it is important to note that the scheduler should
# work properly and be designed to fall back to a basic behavior in case any of the optional parameters has unique
# values. For example, this means it must handle the zero value as a requested pod resource, etc.

### Define input graph

DEF_PRIVACY_ZONE = "default"
PRIVACY_ZONE_X = "Zone_X"
PRIVACY_ZONE_Y = "Zone_Y"

NODE_A = "Node_A"
NODE_B = "Node_B"

################ Define pods

# Modest-demanding pod with near-data processing and SSD preference
pod_i = {
    "demand": {  # Default: 0
        "cpu": 1000,  # Default: 0
        "memory": 100000,  # Default: 0
        "storage": 10000,  # Default: 0
        "ssd": False,  # Default: False
        "gpu": False  # Default: False
    },
    "prefer": {
        "cpu": 2000,
        "memory": 200000,
        "storage": 10000,
        "ssd": True,
        "gpu": False
    },
    "zone": {
        DEF_PRIVACY_ZONE: True,  # Mandatory | default zone: 'default'
        PRIVACY_ZONE_X: True
    },
    "collocated": True,  # Mandatory | default: False
    "metadata": {  # metadata should ignored by scheduler
        "name": "Pod_1"
    }
}

# High-demanding pod with GPU acceleration requirement and no storage constraint
pod_j = {
    "demand": {
        "cpu": 4000,
        "memory": 200000,
        "storage": 0,
        "ssd": False,
        "gpu": True
    },
    "prefer": {
        "cpu": 8000,
        "memory": 1000000,
        "storage": 0,
        "ssd": True,
        "gpu": True
    },
    "zone": {  # List of eligible zones | Mandatory | default: default
        PRIVACY_ZONE_Y: True
    },
    "collocated": False,
    "metadata": {
        "name": "Pod_2"
    }
}

################ Define physical nodes

# Low-resource node
node_a = {
    "resource": {  # Available resources = [capacity] - [pod resources] | Mandatory
        "cpu": 32000 - pod_i["prefer"]["cpu"],
        "memory": 8192000 - pod_i["prefer"]["memory"],
        "storage": 1000000 - pod_i["prefer"]["storage"]
    },
    "capacity": {  # All node resources | Mandatory
        "cpu": 32000,  # milliCPU (K8s min unit)
        "memory": 8192000,  # KiB (K8s min unit)
        "storage": 1000000  # KiB (K8s min unit)
    },
    "zone": {  # Mandatory
        DEF_PRIVACY_ZONE: True,
        PRIVACY_ZONE_X: True,
        PRIVACY_ZONE_Y: False  # Optional - zones not belonging to the node can be omitted
    },
    "pdc": True,  # Mandatory
    "capability": {  # Defaults: 0
        "ssd": False,
        "gpu": False
    },
    "pod": {  # Default: "empty"
        pod_i['metadata']['name']: pod_i
    },
    "metadata": {  # metadata should ignored by scheduler
        "name": NODE_A,
        "ip": "192.168.0.1",
        "architecture": "amd64",
        "os": "Linux"
    }
}

# High-resource node
node_b = {
    "resource": {
        "cpu": 64000,
        "memory": 10240000,
        "storage": 1000000
    },
    "capacity": {
        "cpu": 64000,
        "memory": 10240000,
        "storage": 1000000
    },
    "zone": {  # Mandatory
        DEF_PRIVACY_ZONE: True,
        PRIVACY_ZONE_X: True,
        PRIVACY_ZONE_Y: True
    },
    "pdc": False,  # Mandatory
    "capability": {  # Defaults: False
        "ssd": True,
        "gpu": True},
    "pod": {},  # Default: "empty"
    "metadata": {  # metadata should ignored by scheduler
        "name": NODE_B,
        "ip": "192.168.0.2",
        "architecture": "amd64",
        "os": "Linux"
    }
}

################ Define edge parameters

edge_ab = {  # Defaults: 0 / inf
    "delay": 10,  # ms
    "bw": 100  # Mbps
}

################ K3s test topology

k3s_topo_data = {
    "k3d-dev-agent-0": {
        "resource": {
            "cpu": 4000,
            "memory": 5035316,
            "storage": 95904111
        },
        "capacity": {
            "cpu": 4000,
            "memory": 5035316,
            "storage": 95904111
        },
        "zone": {
            "default": True,
            "zone_A": True,
            "zone_B": True
        },
        "pdc": True,
        "capability": {
            "ssd": False,
            "gpu": True
        },
        "pod": {
            "scheduler": {
                "priority": 0,
                "demand": {
                    "cpu": 0,
                    "memory": 0,
                    "storage": 0,
                    "ssd": False,
                    "gpu": False
                },
                "prefer": {
                    "cpu": 0,
                    "memory": 0,
                    "storage": 0,
                    "ssd": False,
                    "gpu": False
                },
                "zone": {
                    "default": True
                },
                "collocated": False,
                "metadata": {
                    "name": "scheduler",
                    "namespace": "ptx-edge",
                    "created": "2025-12-01T13:40:20Z",
                    "scheduler": "default-scheduler",
                    "status": "Running",
                    "labels": {
                        "app": "scheduler"
                    }
                }
            }
        },
        "metadata": {
            "name": "k3d-dev-agent-0",
            "architecture": "amd64",
            "os": "linux",
            "kernel": "6.8.0-87-generic",
            "ip": "172.21.0.3"
        }
    },
    "k3d-dev-server-0": {
        "resource": {
            "cpu": 4000,
            "memory": 5035316,
            "storage": 95904111
        },
        "capacity": {
            "cpu": 4000,
            "memory": 5035316,
            "storage": 95904111
        },
        "zone": {
            "default": True
        },
        "pdc": False,
        "capability": {
            "ssd": True,
            "gpu": False
        },
        "pod": {},
        "metadata": {
            "name": "k3d-dev-server-0",
            "architecture": "amd64",
            "os": "linux",
            "kernel": "6.8.0-87-generic",
            "ip": "172.21.0.2"
        }
    }
}

k3s_pod_data = {
    "test": {
        "priority": 0,
        "demand": {
            "cpu": 100,
            "memory": 92160,
            "storage": 0,
            "ssd": False,
            "gpu": False
        },
        "prefer": {
            "cpu": 500,
            "memory": 317440,
            "storage": 0,
            "ssd": False,
            "gpu": False
        },
        "zone": {
            "zone_A": True
        },
        "collocated": True,
        "metadata": {
            "name": "test",
            "namespace": "ptx-edge",
            "created": "2025-12-01T14:34:36Z",
            "scheduler": "ptx-edge-scheduler",
            "status": "Pending",
            "labels": {
                "app": "worker"
            }
        }
    }
}

################ Serialize input/output

if __name__ == '__main__':
    topo = nx.Graph(name='topology')
    pod = nx.Graph(name='pod')
    topo.add_node("node-a", **node_a)
    topo.add_node("node-b", **node_b)
    topo.add_edge("node-a", "node-b", **edge_ab)

    # print(json.dumps(dict(topo.nodes()), indent=4, sort_keys=False))
    # print(json.dumps(dict(topo.adjacency()), indent=4, sort_keys=False))

    pod.add_node("pod", **pod_j)

    # print(json.dumps(dict(pod.nodes()), indent=4, sort_keys=False))
    # print(json.dumps(dict(pod.adjacency()), indent=4, sort_keys=False))

    nx.write_gml(topo, "example_input_topology.gml")
    nx.write_gml(pod, "example_input_pod.gml")

    with open("output.txt", 'w') as f:
        f.write(NODE_B)

    #####################################################################

    k3s_topo = nx.Graph(name='topology')
    k3s_pod = nx.Graph(name='pod')

    for n, d in k3s_topo_data.items():
        k3s_topo.add_node(n, **d)

    for n, d in k3s_pod_data.items():
        k3s_pod.add_node(n, **d)

    nx.write_gml(k3s_topo, "example_k3s_topology.gml")
    nx.write_gml(k3s_pod, "example_k3s_pod.gml")
