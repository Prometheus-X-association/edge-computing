#!/usr/bin/env python3
# Copyright 2025 Janos Czentye
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

### Define input graph
topo = nx.Graph(name='topology')
pod = nx.Graph(name='pod')

PRIVACY_ZONE_X = "Zone_X"
PRIVACY_ZONE_Y = "Zone_Y"

NODE_A = "Node_A"
NODE_B = "Node_B"

################ Define pods

# Modest-demanding pod with near-data processing and SSD preference
pod_i = {
    "demand": {  # Defaults: 0
        "cpu": 1,
        "memory": 100,
        "storage": 10,
        "ssd": False,
        "gpu": False
    },
    "prefer": {  # Defaults: 0
        "cpu": 2,
        "memory": 200,
        "storage": 10,
        "ssd": True,
        "gpu": False
    },
    "zone": PRIVACY_ZONE_X,  # Mandatory
    "collocated": True,  # Mandatory
    "metadata": {  # metadata should ignored by scheduler
        "name": "Pod_1"
    }
}

# High-demanding pod with GPU acceleration requirement and no storage constraint
pod_j = {
    "demand": {  # Defaults: 0
        "cpu": 4,
        "memory": 200,
        "storage": 0,
        "ssd": False,
        "gpu": True
    },
    "prefer": {  # Defaults: 0
        "cpu": 8,
        "memory": 1000,
        "storage": 0,
        "ssd": True,
        "gpu": True
    },
    "zone": PRIVACY_ZONE_Y,  # Mandatory
    "collocated": False,  # Mandatory
    "metadata": {  # metadata should ignored by scheduler
        "name": "Pod_2"
    }
}

################ Define physical nodes

# Low-resource node
node_a = {
    "resource": {  # Mandatory
        "cpu": 32,
        "memory": 8192,
        "storage": 1000
    },
    "zones": {  # Mandatory
        PRIVACY_ZONE_X: True,
        PRIVACY_ZONE_Y: False  # Optional - zones not belonging to the node can be omitted
    },
    "pdc": True,  # Mandatory
    "capability": {  # Defaults: 0
        "ssd": False,
        "gpu": False
    },
    "pods": {  # Default: "empty"
        pod_i['metadata']['name']: pod_i,
        pod_j['metadata']['name']: pod_j
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
    "resource": {  # Mandatory
        "cpu": 64,  # cores
        "memory": 10240,  # Mi
        "storage": 1000
    },
    "zones": {  # Mandatory
        PRIVACY_ZONE_X: True,
        PRIVACY_ZONE_Y: True
    },
    "pdc": False,  # Mandatory
    "capability": {  # Defaults: 0
        "ssd": True,
        "gpu": True},
    "pods": {},  # Default: "empty"
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

################ Assemble graph

topo.add_node("node-a", **node_a)
topo.add_node("node-b", **node_b)
topo.add_edge("node-a", "node-b", **edge_ab)

pod.add_node("pod", **pod_j)

################ Serialize input/output

if __name__ == '__main__':
    nx.write_gml(topo, "input_topology.gml")
    nx.write_gml(pod, "input_pod.gml")

    with open("output.txt", 'w') as f:
        f.write(NODE_B)
