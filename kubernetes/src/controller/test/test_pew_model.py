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

from model.ptxedgeworker import PEW, PEWSpec

raw_kopf_obj = {
    'data': {
        'src': {
            'method': "HTTPS"
        }
    },
    'worker': {
        'location': {
            'method': 'DOCKER'
        }
    }
}


def test_ewt_spec_parsing():
    pprint.pprint(PEW(spec=PEWSpec(**raw_kopf_obj)))


raw_k8s_obj = r"""
{
    "apiVersion": "dataspace.ptx.org/v1alpha1",
    "kind": "PtxEdgeWorker",
    "metadata": {
        "annotations": {
            "kubectl.kubernetes.io/last-applied-configuration": "{\"apiVersion\":\"dataspace.ptx.org/v1alpha1\",\"kind\":\"PtxEdgeWorker\",\"metadata\":{\"annotations\":{},\"labels\":{\"env\":\"test\"},\"name\":\"example\",\"namespace\":\"ptx-edge\"},\"spec\":{\"data\":{\"dst\":{\"method\":\"LOCAL\",\"path\":\"/data\"},\"src\":{\"auth\":{\"insecure\":true,\"scheme\":\"BASIC\",\"secret\":\"admin\",\"user\":\"admin\"},\"method\":\"HTTPS\",\"path\":\"https://github.com:8080/czeni/sample-datasets/raw/refs/heads/main/mnist_train_data.npz\",\"size\":75}},\"dataspace\":{\"exchange\":{\"data\":{\"consumer\":{\"offer\":\"66d18b79ee71f9f096baecb1\",\"resource\":\"66d18bf6ee71f9f096baed58\"},\"contract\":\"66db1a6dc29e3ba863a85e0f\",\"provider\":{\"offer\":\"66d187f4ee71f9f096bae8ca\",\"resource\":\"d66d1889cee71f9f096bae98b\"}},\"worker\":{\"consumer\":{\"offer\":\"77d18b79ee71f9f096baecb1\",\"resource\":\"77d18bf6ee71f9f096baed58\"},\"contract\":\"77db1a6dc29e3ba863a85e0f\",\"provider\":{\"offer\":\"77d187f4ee71f9f096bae8ca\",\"resource\":\"77d1889cee71f9f096bae98b\"}}},\"privacy\":{\"required\":true,\"zones\":[{\"name\":\"zone1\"},{\"name\":\"zone2\",\"preferred\":true}]}},\"service\":{\"enabled\":true,\"interfaces\":[{\"port\":8080},{\"port\":80,\"public\":true,\"secured\":true}]},\"worker\":{\"cached\":true,\"command\":[\"/bin/sh\",\"-c\",\"'sleep infinity'\"],\"config\":{\"env\":[{\"key\":\"WRK_TEST_VAR\",\"value\":\"test123\"}],\"file\":{\"data\":\"{\\n  \\\"test\\\": 42\\n}\\n\",\"path\":\"/var/cache/worker/config.json\"}},\"demands\":{\"cpu\":1.5,\"memory\":500},\"location\":{\"cred\":{\"insecure\":false,\"secret\":\"admin\",\"server\":\"https://index.docker.io/v1/\",\"user\":\"admin\"},\"image\":\"busybox:latest\",\"method\":\"DOCKER\"},\"name\":\"myworker:latest\"}}}\n"
        },
        "creationTimestamp": "2026-08-13T14:15:55Z",
        "generation": 1,
        "labels": {
            "env": "test"
        },
        "name": "example",
        "namespace": "ptx-edge",
        "resourceVersion": "4179",
        "uid": "476549f4-f269-413c-b77a-47b218f7b583"
    },
    "spec": {
        "data": {
            "dst": {
                "method": "LOCAL",
                "path": "/data"
            },
            "src": {
                "auth": {
                    "insecure": true,
                    "scheme": "BASIC",
                    "secret": "admin",
                    "user": "admin"
                },
                "method": "HTTPS",
                "path": "https://github.com:8080/czeni/sample-datasets/raw/refs/heads/main/mnist_train_data.npz",
                "size": 75
            }
        },
        "dataspace": {
            "exchange": {
                "data": {
                    "consumer": {
                        "offer": "66d18b79ee71f9f096baecb1",
                        "resource": "66d18bf6ee71f9f096baed58"
                    },
                    "contract": "66db1a6dc29e3ba863a85e0f",
                    "provider": {
                        "offer": "66d187f4ee71f9f096bae8ca",
                        "resource": "d66d1889cee71f9f096bae98b"
                    }
                },
                "worker": {
                    "consumer": {
                        "offer": "77d18b79ee71f9f096baecb1",
                        "resource": "77d18bf6ee71f9f096baed58"
                    },
                    "contract": "77db1a6dc29e3ba863a85e0f",
                    "provider": {
                        "offer": "77d187f4ee71f9f096bae8ca",
                        "resource": "77d1889cee71f9f096bae98b"
                    }
                }
            },
            "privacy": {
                "required": true,
                "zones": [
                    {
                        "name": "zone1",
                        "preferred": false
                    },
                    {
                        "name": "zone2",
                        "preferred": true
                    }
                ]
            }
        },
        "service": {
            "enabled": true,
            "interfaces": [
                {
                    "port": 8080,
                    "public": false,
                    "secured": false
                },
                {
                    "port": 80,
                    "public": true,
                    "secured": true
                }
            ]
        },
        "worker": {
            "cached": true,
            "command": [
                "/bin/sh",
                "-c",
                "'sleep infinity'"
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
            "demands": {
                "cpu": 1.5,
                "memory": 500
            },
            "location": {
                "cred": {
                    "insecure": false,
                    "secret": "admin",
                    "server": "https://index.docker.io/v1/",
                    "user": "admin"
                },
                "image": "busybox:latest",
                "method": "DOCKER"
            },
            "name": "myworker:latest"
        }
    }
}
"""


def test_k8s_raw_parsing():
    k8s_model = PEW.model_validate_json(raw_k8s_obj)
    pprint.pprint(k8s_model)

    print("Parsed datasource:", k8s_model.spec.data.src.path)
    print("Parsed image:", k8s_model.spec.worker.location.image)


if __name__ == '__main__':
    test_ewt_spec_parsing()
    test_k8s_raw_parsing()
