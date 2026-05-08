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

from model.edgeworkertask import EWT, EWTSpec

raw_kopf_obj = {
    'data': {
        'src': {
            'path': 'https://github.com:80/czeni/sample-datasets/raw/refs/heads/main/mnist_train_data.npz'
        },
        'dst': {
            'path': '/var/cache/data/',
        }
    },
    'worker': {
        'location': {
            'protocol': 'docker',
            'image': 'busybox:latest',
        },
        'name': 'myworker:latest',
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


def test_ewt_spec_parsing():
    pprint.pprint(EWT(spec=EWTSpec(**raw_kopf_obj)))


raw_k8s_obj = r"""
{
    "apiVersion": "dataspace.ptx.org/v1alpha1",
    "kind": "EdgeWorkerTask",
    "metadata": {
        "annotations": {
            "dataspace.ptx.org/kopf-managed": "yes",
            "dataspace.ptx.org/last-handled-configuration": "{\"spec\":{\"data\":{\"dst\":{\"path\":\"/var/cache/data/\",\"scheme\":\"local\"},\"src\":{\"auth\":{\"method\":\"basic\",\"secret\":\"admin\",\"user\":\"admin\"},\"path\":\"https://github.com:8080/czeni/sample-datasets/raw/refs/heads/main/mnist_train_data.npz\",\"scheme\":\"https\"}},\"dataspace\":{\"offer\":{\"consumer\":\"66d18b79ee71f9f096baecb1\",\"provider\":\"66d187f4ee71f9f096bae8ca\"}},\"service\":{\"enabled\":true,\"interfaces\":[{\"port\":8080,\"public\":false,\"secured\":false},{\"port\":80,\"public\":true,\"secured\":true}]},\"worker\":{\"cached\":true,\"command\":[\"/bin/bash\",\"date\"],\"config\":{\"env\":[{\"key\":\"WRK_TEST_VAR\",\"value\":\"test123\"}],\"file\":{\"data\":\"{\\n  \\\"test\\\": 42\\n}\\n\",\"path\":\"/var/cache/worker/config.json\"}},\"location\":{\"cred\":{\"insecure\":false,\"secret\":\"admin\",\"server\":\"https://index.docker.io/v1/\",\"user\":\"admin\"},\"image\":\"busybox:latest\",\"protocol\":\"docker\"},\"name\":\"myworker:latest\"}},\"metadata\":{\"labels\":{\"env\":\"test\"}}}\n",
            "kubectl.kubernetes.io/last-applied-configuration": "{\"apiVersion\":\"dataspace.ptx.org/v1alpha1\",\"kind\":\"EdgeWorkerTask\",\"metadata\":{\"annotations\":{},\"labels\":{\"env\":\"test\"},\"name\":\"test-example\",\"namespace\":\"ptx-edge\"},\"spec\":{\"data\":{\"dst\":{\"path\":\"/var/cache/data/\",\"scheme\":\"local\"},\"src\":{\"auth\":{\"method\":\"basic\",\"secret\":\"admin\",\"user\":\"admin\"},\"path\":\"https://github.com:8080/czeni/sample-datasets/raw/refs/heads/main/mnist_train_data.npz\",\"scheme\":\"https\"}},\"dataspace\":{\"offer\":{\"consumer\":\"66d18b79ee71f9f096baecb1\",\"provider\":\"66d187f4ee71f9f096bae8ca\"}},\"service\":{\"enabled\":true,\"interfaces\":[{\"port\":8080},{\"port\":80,\"public\":true,\"secured\":true}]},\"worker\":{\"cached\":true,\"command\":[\"/bin/bash\",\"date\"],\"config\":{\"env\":[{\"key\":\"WRK_TEST_VAR\",\"value\":\"test123\"}],\"file\":{\"data\":\"{\\n  \\\"test\\\": 42\\n}\\n\",\"path\":\"/var/cache/worker/config.json\"}},\"location\":{\"cred\":{\"insecure\":false,\"secret\":\"admin\",\"server\":\"https://index.docker.io/v1/\",\"user\":\"admin\"},\"image\":\"busybox:latest\",\"protocol\":\"docker\"},\"name\":\"myworker:latest\"}}}\n"
        },
        "creationTimestamp": "2026-05-08T11:45:04Z",
        "generation": 1,
        "labels": {
            "env": "test"
        },
        "name": "test-example",
        "namespace": "ptx-edge",
        "resourceVersion": "6380",
        "uid": "48283b1c-f3ac-4e10-a748-6b3dc6d40676"
    },
    "spec": {
        "data": {
            "dst": {
                "path": "/var/cache/data/",
                "scheme": "local"
            },
            "src": {
                "auth": {
                    "method": "basic",
                    "secret": "admin",
                    "user": "admin"
                },
                "path": "https://github.com:8080/czeni/sample-datasets/raw/refs/heads/main/mnist_train_data.npz",
                "scheme": "https"
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
            "location": {
                "cred": {
                    "insecure": false,
                    "secret": "admin",
                    "server": "https://index.docker.io/v1/",
                    "user": "admin"
                },
                "image": "busybox:latest",
                "protocol": "docker"
            },
            "name": "myworker:latest"
        }
    },
    "status": {
        "create": {
            "initialized": true
        }
    }
}
"""


def test_k8s_raw_parsing():
    k8s_model = EWT.model_validate_json(raw_k8s_obj)
    pprint.pprint(k8s_model)

    print("Parsed datasource:", k8s_model.spec.data.src.path)
    print("Parsed image:", k8s_model.spec.worker.location.image)


if __name__ == '__main__':
    test_ewt_spec_parsing()
    test_k8s_raw_parsing()
