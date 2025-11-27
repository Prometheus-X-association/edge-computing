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


def get_pods_by_node(node: str, ns: str) -> typing.Generator[client.V1Pod, None, None]:
    """

    :return:
    """
    for pod in client.CoreV1Api().list_namespaced_pod(namespace=ns, field_selector=f"spec.nodeName={node}").items:
        if pod.status.phase == "Running":
            yield pod


def assign_pod_to_node(pod: str, ns: str, node: str, scheduler: str, method: str) -> bool | None:
    """
    
    :param pod: 
    :param ns: 
    :param node: 
    :param scheduler: 
    :param method: 
    :return: 
    """
    log.info(f"Assigning pod[{pod}] to node[{node}]...")
    binding_body = client.V1Binding(metadata=client.V1ObjectMeta(name=pod,
                                                                 namespace=ns),
                                    target=client.V1ObjectReference(kind='Node',
                                                                    name=node))
    log.debug(f"Created binding body:\n{json.dumps(deep_filter(binding_body.to_dict()), indent=4, default=str)}")
    try:
        # Disable automatic response deserialization to bypass issue: https://github.com/kubernetes-client/python/issues/825
        client.CoreV1Api().create_namespaced_binding(namespace=ns, body=binding_body, _preload_content=False)
        raise_successful_k8s_scheduling_event(pod=pod, ns=ns, node=node, scheduler=scheduler, method=method)
        return True
    except client.ApiException as e:
        log.error(f"Error received:\n{e}")
        raise_failed_k8s_scheduling_event(pod=pod, ns=ns, scheduler=scheduler, method=method, reason=e.reason)


def create_scheduling_event(pod: str, ns: str, scheduler: str, level: str, result: str, msg: str) -> client.CoreV1Event:
    """

    :param pod:
    :param ns:
    :param scheduler:
    :param level:
    :param result:
    :param msg:
    :return:
    """
    log.info(f"Create scheduling event for pod[{pod}]...")
    timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    event_body = client.CoreV1Event(metadata=client.V1ObjectMeta(namespace=ns,
                                                                 name=f"{pod}.{time.time()}",
                                                                 creation_timestamp=timestamp),
                                    type=level,
                                    action="Binding",
                                    reason=result,
                                    message=msg,
                                    involved_object=client.V1ObjectReference(kind="Pod",
                                                                             name=pod,
                                                                             namespace=ns),
                                    reporting_component=scheduler,
                                    first_timestamp=timestamp,
                                    last_timestamp=timestamp)
    log.debug(f"Created event body:\n{json.dumps(deep_filter(event_body.to_dict()), indent=4, default=str)}")
    return event_body


def raise_successful_k8s_scheduling_event(pod: str, ns: str, node: str, scheduler: str, method: str):
    """
    
    :param pod: 
    :param ns: 
    :param node: 
    :param scheduler: 
    :param method: 
    :return: 
    """
    event_body = create_scheduling_event(pod=pod, ns=ns, scheduler=scheduler, level="Normal", result="Scheduled",
                                         msg=f"Successfully assigned {ns}/{pod} to {node} "
                                             f"by scheduler: {scheduler}[{method}]")
    try:
        client.CoreV1Api().create_namespaced_event(namespace=ns, body=event_body)
    except client.ApiException as e:
        log.error(f"Error received:\n{e}")


def raise_failed_k8s_scheduling_event(pod: str, ns: str, scheduler: str, method: str, reason: str = "Unexpected error"):
    """

    :param pod:
    :param ns:
    :param scheduler:
    :param method:
    :param reason:
    :return:
    """
    event_body = create_scheduling_event(pod=pod, ns=ns, scheduler=scheduler, level="Warning", result="Failed",
                                         msg=f"Failed to assign {ns}/{pod} to a node "
                                             f"by scheduler: {scheduler}[{method}]. "
                                             f"Reason: {reason}")
    try:
        client.CoreV1Api().create_namespaced_event(namespace=ns, body=event_body)
    except client.ApiException as e:
        log.error(f"Error received:\n{e}")
