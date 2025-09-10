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


def assign_pod_to_node(pod_name: str, node_name: str, namespace: str, scheduler: str) -> bool | None:
    """

    :param pod_name:
    :param node_name:
    :param namespace:
    :param scheduler:
    :return:
    """
    log.info(f"Assigning pod[{pod_name}] to node[{node_name}]...")
    binding_body = client.V1Binding(metadata=client.V1ObjectMeta(name=pod_name,
                                                                 namespace=namespace),
                                    target=client.V1ObjectReference(kind='Node',
                                                                    name=node_name))
    log.debug(f"Created binding body:\n{json.dumps(deep_filter(binding_body.to_dict()), indent=4, default=str)}")
    try:
        # Disable automatic response deserialization to bypass issue: https://github.com/kubernetes-client/python/issues/825
        client.CoreV1Api().create_namespaced_binding(namespace=namespace, body=binding_body, _preload_content=False)
        create_successful_scheduling_event(scheduler=scheduler, pod_name=pod_name, node_name=node_name,
                                           namespace=namespace)
        return True
    except client.ApiException as e:
        log.error(f"Error received:\n{e}")
        create_failed_scheduling_event(scheduler=scheduler, pod_name=pod_name, namespace=namespace, reason=e.reason)


def __create_scheduling_event(scheduler: str, pod_name: str, namespace: str, level: str, result: str,
                              message: str) -> client.CoreV1Event:
    """

    :param scheduler:
    :param pod_name:
    :param namespace:
    :param level:
    :param result:
    :param message:
    :return:
    """
    log.info(f"Create scheduling event for pod[{pod_name}]...")
    timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    event_body = client.CoreV1Event(metadata=client.V1ObjectMeta(namespace=namespace,
                                                                 name=f"{pod_name}.{time.time()}",
                                                                 creation_timestamp=timestamp),
                                    type=level,
                                    action="Binding",
                                    reason=result,
                                    message=message,
                                    involved_object=client.V1ObjectReference(kind="Pod",
                                                                             name=pod_name,
                                                                             namespace=namespace),
                                    reporting_component=scheduler,
                                    first_timestamp=timestamp, last_timestamp=timestamp)
    log.debug(f"Created event body:\n{json.dumps(deep_filter(event_body.to_dict()), indent=4, default=str)}")
    return event_body


def create_successful_scheduling_event(scheduler: str, pod_name: str, namespace: str, node_name: str):
    """

    :param scheduler:
    :param pod_name:
    :param namespace:
    :param node_name:
    :return:
    """
    event_body = __create_scheduling_event(scheduler=scheduler, pod_name=pod_name, namespace=namespace,
                                           level="Normal", result="Scheduled",
                                           message=f"Successfully assigned {namespace}/{pod_name} to {node_name} "
                                                   f"by scheduler: {scheduler}")
    try:
        client.CoreV1Api().create_namespaced_event(namespace=namespace, body=event_body)
    except client.ApiException as e:
        log.error(f"Error received:\n{e}")


def create_failed_scheduling_event(scheduler: str, pod_name: str, namespace: str, reason: str = "Unexpected error"):
    """

    :param scheduler:
    :param pod_name:
    :param namespace:
    :param reason:
    :return:
    """
    event_body = __create_scheduling_event(scheduler=scheduler, pod_name=pod_name, namespace=namespace,
                                           level="Warning", result="Failed",
                                           message=f"Failed to assign {namespace}/{pod_name} to a node by scheduler: "
                                                   f"{scheduler}. Reason: {reason}")
    try:
        client.CoreV1Api().create_namespaced_event(namespace=namespace, body=event_body)
    except client.ApiException as e:
        log.error(f"Error received:\n{e}")
