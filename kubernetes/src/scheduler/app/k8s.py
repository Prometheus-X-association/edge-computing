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


def assign_pod_to_node(pod: client.V1Pod, ns: str, node_meta: dict[str, ...], scheduler: str,
                       method: str) -> bool | None:
    """
    
    :param pod:
    :param ns:
    :param node_meta:
    :param scheduler:
    :param method: 
    :return: 
    """
    log.info(f"Assigning pod[{pod.metadata.name}] to node[{node_meta["name"]}]...")
    binding_body = client.V1Binding(metadata=client.V1ObjectMeta(name=pod.metadata.name,
                                                                 namespace=ns),
                                    target=client.V1ObjectReference(api_version=node_meta['api_version'],
                                                                    kind=node_meta['kind'],
                                                                    name=node_meta['name'],
                                                                    namespace=None,
                                                                    resource_version=node_meta['resource_version'],
                                                                    uid=node_meta['uid']))
    log.debug(f"Created binding body:\n{json.dumps(deep_filter(binding_body.to_dict()), indent=4, default=str)}")
    try:
        # Disable automatic response deserialization to bypass issue: https://github.com/kubernetes-client/python/issues/825
        client.CoreV1Api().create_namespaced_binding(namespace=ns, body=binding_body, _preload_content=False)
        raise_successful_k8s_scheduling_event(pod=pod, ns=ns, node=node_meta["name"], scheduler=scheduler,
                                              method=method)
        return True
    except client.ApiException as e:
        log.error(f"Error received:\n{e}")
        raise_failed_k8s_scheduling_event(pod=pod, ns=ns, scheduler=scheduler, method=method, reason=e.reason)


def create_scheduling_event(pod: client.V1Pod, ns: str, scheduler: str,
                            level: str, result: str, msg: str) -> client.CoreV1Event:
    """

    :param pod:
    :param ns:
    :param scheduler:
    :param level:
    :param result:
    :param msg:
    :return:
    """
    log.info(f"Create scheduling event for pod[{pod.metadata.name}]...")
    timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    event_body = client.CoreV1Event(metadata=client.V1ObjectMeta(namespace=ns,
                                                                 name=f"{pod.metadata.name}.{time.time()}",
                                                                 creation_timestamp=timestamp),
                                    type=level,
                                    action="Binding",
                                    reason=result,
                                    message=msg,
                                    involved_object=client.V1ObjectReference(
                                        api_version=pod.api_version,
                                        kind=pod.kind,
                                        name=pod.metadata.name,
                                        namespace=pod.metadata.namespace,
                                        resource_version=pod.metadata.resource_version,
                                        uid=pod.metadata.uid),
                                    reporting_component="default-scheduler",
                                    reporting_instance="default-scheduler",
                                    event_time=timestamp)
    log.debug(f"Created event body:\n{json.dumps(deep_filter(event_body.to_dict()), indent=4, default=str)}")
    return event_body


def raise_successful_k8s_scheduling_event(pod: client.V1Pod, ns: str, node: str, scheduler: str, method: str):
    """
    
    :param pod: 
    :param ns: 
    :param node: 
    :param scheduler: 
    :param method: 
    :return: 
    """
    event_body = create_scheduling_event(pod=pod, ns=ns, scheduler=scheduler, level="Normal", result="Scheduled",
                                         msg=f"Successfully assigned {ns}/{pod.metadata.name} to {node} "
                                             f"by scheduler: {scheduler}[{method}]")
    try:
        client.CoreV1Api().create_namespaced_event(namespace=ns, body=event_body)
    except client.ApiException as e:
        log.error(f"Error received:\n{e}")


def raise_failed_k8s_scheduling_event(pod: client.V1Pod, ns: str, scheduler: str, method: str,
                                      reason: str = "Unexpected error"):
    """

    :param pod:
    :param ns:
    :param scheduler:
    :param method:
    :param reason:
    :return:
    """
    event_body = create_scheduling_event(pod=pod, ns=ns, scheduler=scheduler, level="Warning", result="Failed",
                                         msg=f"Failed to assign {ns}/{pod.metadata.name} to a node "
                                             f"by scheduler: {scheduler}[{method}]. "
                                             f"Reason: {reason}")
    try:
        client.CoreV1Api().create_namespaced_event(namespace=ns, body=event_body)
    except client.ApiException as e:
        log.error(f"Error received:\n{e}")
