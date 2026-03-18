#!/usr/bin/env python3
# Copyright 2026 Janos Czentye
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
import pprint

from model.edgeworkertask import EdgeWorkerTask, EdgeWorkerTaskSpec

raw_kopf_obj = {
    'data': {
        'source': {
            'location': 'https://github.com:80/czeni/sample-datasets/raw/refs/heads/main/mnist_train_data.npz'
        },
        'path': '/var/cache/data/',
    },
    'worker': {
        'source': {
            'scheme': 'docker',
            'location': 'busybox:latest',
        },
        'image': 'myworker:latest',
        'config': {
            'env': [
                {
                    'key': 'MY_VAR',
                    'value': "test"
                }
            ]
        }
    }
}

pprint.pprint(EdgeWorkerTask(spec=EdgeWorkerTaskSpec(**raw_kopf_obj)))

raw_k8s_obj = r"""
{
    "apiVersion": "dataspace.ptx.org/v1alpha1",
    "kind": "EdgeWorkerTask",
    "metadata": {
        "annotations": {
            "kubectl.kubernetes.io/last-applied-configuration": "{\"apiVersion\":\"dataspace.ptx.org/v1alpha1\",\"kind\":\"EdgeWorkerTask\",\"metadata\":{\"annotations\":{},\"labels\":{\"env\":\"test\"},\"name\":\"test-ewt\",\"namespace\":\"ptx-edge\"},\"spec\":{\"data\":{\"auth\":{\"method\":\"basic\",\"secret\":\"admin\",\"user\":\"admin\"},\"path\":\"/var/cache/data/\",\"source\":{\"location\":\"https://github.com:8080/czeni/sample-datasets/raw/refs/heads/main/mnist_train_data.npz\"}},\"dataspace\":{\"offer\":{\"consumer\":\"66d18b79ee71f9f096baecb1\",\"provider\":\"66d187f4ee71f9f096bae8ca\"}},\"service\":{\"enabled\":true,\"interfaces\":[{\"port\":8080},{\"port\":80,\"public\":true}]},\"worker\":{\"auth\":{\"insecure\":false,\"secret\":\"admin\",\"server\":\"https://index.docker.io/v1/\",\"user\":\"admin\"},\"command\":[\"/bin/bash\",\"date\"],\"config\":{\"env\":[{\"key\":\"WRK_TEST_VAR\",\"value\":\"test123\"}],\"file\":{\"data\":\"{\\n  \\\"test\\\": 42\\n}\\n\",\"path\":\"/var/cache/worker/config.json\"}},\"image\":\"myworker:latest\",\"source\":{\"location\":\"busybox:latest\",\"scheme\":\"docker\"}}}}\n"
        },
        "creationTimestamp": "2026-03-18T20:46:17Z",
        "generation": 1,
        "labels": {
            "env": "test"
        },
        "name": "test-ewt",
        "namespace": "ptx-edge",
        "resourceVersion": "7951",
        "uid": "18cef8a1-d2f7-4111-b781-285849d37335"
    },
    "spec": {
        "data": {
            "auth": {
                "method": "basic",
                "secret": "admin",
                "user": "admin"
            },
            "path": "/var/cache/data/",
            "source": {
                "location": "https://github.com:8080/czeni/sample-datasets/raw/refs/heads/main/mnist_train_data.npz"
            }
        },
        "dataspace": {
            "offer": {
                "consumer": "66d18b79ee71f9f096baecb1",
                "provider": "66d187f4ee71f9f096bae8ca"
            }
        },
        "service": {
            "enabled": true,
            "interfaces": [
                {
                    "port": 8080,
                    "public": false
                },
                {
                    "port": 80,
                    "public": true
                }
            ]
        },
        "worker": {
            "auth": {
                "insecure": false,
                "secret": "admin",
                "server": "https://index.docker.io/v1/",
                "user": "admin"
            },
            "cached": true,
            "command": [
                "/bin/bash",
                "date"
            ],
            "config": {
                "env": [
                    {
                        "key": "WRK_TEST_VAR",
                        "value": "test123"
                    }
                ],
                "file": {
                    "data": "{\n  \"test\": 42\n}\n",
                    "path": "/var/cache/worker/config.json"
                }
            },
            "image": "myworker:latest",
            "source": {
                "location": "busybox:latest",
                "scheme": "docker"
            }
        }
    }
}
"""

pprint.pprint(EdgeWorkerTask.model_validate_json(raw_k8s_obj))
