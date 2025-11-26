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
import datetime
import json
import logging
import time
import typing

from kubernetes import client

from app.scheduler import CONFIG
from app.utils import deep_filter

log = logging.getLogger(__name__)


def get_available_nodes() -> typing.Generator[client.V1Node, None, None]:
    """

    :return:
    """
    for node in client.CoreV1Api().list_node(field_selector="spec.unschedulable=false").items:
        for status in node.status.conditions:
            if status.status == "True" and status.type == "Ready":
                yield node


def assign_pod_to_node(pod_name: str, node_name: str) -> bool | None:
    """

    :param pod_name:
    :param node_name:
    :return:
    """
    log.info(f"Assigning pod[{pod_name}] to node[{node_name}]...")
    binding_body = client.V1Binding(metadata=client.V1ObjectMeta(name=pod_name,
                                                                 namespace=CONFIG['namespace']),
                                    target=client.V1ObjectReference(kind='Node',
                                                                    name=node_name))
    log.debug(f"Created binding body:\n{json.dumps(deep_filter(binding_body.to_dict()), indent=4, default=str)}")
    try:
        # Disable automatic response deserialization to bypass issue: https://github.com/kubernetes-client/python/issues/825
        client.CoreV1Api().create_namespaced_binding(namespace=CONFIG['namespace'], body=binding_body,
                                                     _preload_content=False)
        create_successful_scheduling_event(pod_name=pod_name, node_name=node_name)
        return True
    except client.ApiException as e:
        log.error(f"Error received:\n{e}")
        create_failed_scheduling_event(pod_name=pod_name, reason=e.reason)


def __create_scheduling_event(pod_name: str, level: str, result: str, message: str) -> client.CoreV1Event:
    """

    :param pod_name:
    :param level:
    :param result:
    :param message:
    :return:
    """
    log.info(f"Create scheduling event for pod[{pod_name}]...")
    timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    event_body = client.CoreV1Event(metadata=client.V1ObjectMeta(namespace=CONFIG['namespace'],
                                                                 name=f"{pod_name}.{time.time()}",
                                                                 creation_timestamp=timestamp),
                                    type=level,
                                    action="Binding",
                                    reason=result,
                                    message=message,
                                    involved_object=client.V1ObjectReference(kind="Pod",
                                                                             name=pod_name,
                                                                             namespace=CONFIG['namespace']),
                                    reporting_component=CONFIG['scheduler'],
                                    first_timestamp=timestamp, last_timestamp=timestamp)
    log.debug(f"Created event body:\n{json.dumps(deep_filter(event_body.to_dict()), indent=4, default=str)}")
    return event_body


def create_successful_scheduling_event(pod_name: str, node_name: str):
    """

    :param pod_name:
    :param node_name:
    :return:
    """
    event_body = __create_scheduling_event(pod_name=pod_name, level="Normal", result="Scheduled",
                                           message=f"Successfully assigned {CONFIG['namespace']}/{pod_name} "
                                                   f"to {node_name} "
                                                   f"by scheduler: {CONFIG['scheduler']}[{CONFIG['method']}]")
    try:
        client.CoreV1Api().create_namespaced_event(namespace=CONFIG['namespace'], body=event_body)
    except client.ApiException as e:
        log.error(f"Error received:\n{e}")


def create_failed_scheduling_event(pod_name: str, reason: str = "Unexpected error"):
    """

    :param pod_name:
    :param reason:
    :return:
    """
    event_body = __create_scheduling_event(pod_name=pod_name, level="Warning", result="Failed",
                                           message=f"Failed to assign {CONFIG['namespace']}/{pod_name} to a node "
                                                   f"by scheduler: {CONFIG['scheduler']}[{CONFIG['method']}]. "
                                                   f"Reason: {reason}")
    try:
        client.CoreV1Api().create_namespaced_event(namespace=CONFIG['namespace'], body=event_body)
    except client.ApiException as e:
        log.error(f"Error received:\n{e}")
