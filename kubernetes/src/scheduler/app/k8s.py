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
import json
import logging
import typing

from kubernetes import client

from app.utils import deep_filter

log = logging.getLogger(__name__)


def get_available_nodes() -> typing.Generator[client.V1Node, None, None]:
    for node in client.CoreV1Api().list_node(field_selector="spec.unschedulable=false").items:
        for status in node.status.conditions:
            if status.status == "True" and status.type == "Ready":
                yield node


def assign_pod_to_node(pod_name: str, node_name: str, namespace: str) -> bool | None:
    log.info(f"Assigning pod[{pod_name}] to node[{node_name}]...")
    binding_body = client.V1Binding(metadata=client.V1ObjectMeta(name=pod_name,
                                                                 namespace=namespace),
                                    target=client.V1ObjectReference(kind='Node',
                                                                    name=node_name))
    log.debug(f"Created binding body:\n{json.dumps(deep_filter(binding_body.to_dict()), indent=4, default=str)}")
    try:
        # Disable automatic response deserialization to bypass issue: https://github.com/kubernetes-client/python/issues/825
        client.CoreV1Api().create_namespaced_binding(namespace=namespace, body=binding_body, _preload_content=False)
        return True
    except client.ApiException as e:
        log.error(f"Error received:\n{e}")
