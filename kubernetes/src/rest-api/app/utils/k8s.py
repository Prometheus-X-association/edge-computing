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
import asyncio
import enum
import os
import pprint
import sys
import typing

import fastapi
from fastapi import Query
from kubernetes_asyncio import client, config, watch

from app.model.errors import raise_for_k8s_error
from app.model.ptxedgeworker import PEW
from app.utils.config import CONFIG
from app.utils.helper import str2bool, assemble_worker_endpoint_url, get_k8s_obj_res
from app.utils.logger import logger, sanitize_model

K8sLabelCollectionType = typing.Annotated[
    list[typing.Annotated[str, Query(pattern=r"^(.+)=(.+){1,63}$")]] | None,
    Query(description="Additional k8s-compatible labels", examples=["tier=worker"])]


########################################################################################################################

async def setup_k8s_client() -> None:
    try:
        logger.debug("Loading in-cluster K8s configuration....")
        config.load_incluster_config()
    except config.ConfigException as e:
        logger.error(f"Error loading Kubernetes API config:\n{e}")
        sys.exit(os.EX_CONFIG)


class K8sAPIMethod(enum.StrEnum):
    CREATE = "create"
    GET = "get"
    LIST = "list"
    DELETE = "delete"
    DELETE_ALL = "delete_collection"


async def invoke_k8s_pew_api(method: K8sAPIMethod,
                             body: dict[str, typing.Any] | object | None = None,
                             name: str | None = None,
                             status: bool = False,
                             label_selector: typing.Sequence[str] | None = None,
                             **call_args) -> tuple[dict[str, typing.Any], int]:
    async with client.ApiClient() as api_client:
        api = client.CustomObjectsApi(api_client=api_client)
        logger.info(f"Invoke k8s {api.__class__.__name__}...")
        params = dict(group=PEW.group,
                      version=PEW.version,
                      namespace=CONFIG.WORKER_NS,
                      plural=PEW.plural)
        if body:
            params["body"] = body
        if name:
            params["name"] = name
        if method in (K8sAPIMethod.LIST, K8sAPIMethod.DELETE_ALL) and label_selector:
            params["label_selector"] = label_selector if isinstance(label_selector, str) else ",".join(label_selector)
        if method is K8sAPIMethod.CREATE:
            params['field_manager'] = CONFIG.field_manager
        params.update(call_args)
        logger.debug(f"Assembled k8s API request parameters:\n{pprint.pformat(params, sort_dicts=False)}")
        caller = "namespaced_custom_object_status" if status else "namespaced_custom_object"
        api_caller = getattr(api, f"{method.value}_{caller}_with_http_info")
        obj, status, _ = await api_caller(**params)
        return obj, status


async def assemble_worker_endpoints(request: fastapi.Request,
                                    name: str,
                                    obj: dict[str, typing.Any] | None = None) -> list[dict[str, typing.Any]]:
    if not obj:
        obj, _status = await invoke_k8s_pew_api(method=K8sAPIMethod.GET, name=name, status=True)
        raise_for_k8s_error(obj=obj, status=_status)
        logger.debug(f"Obtained response:\n{sanitize_model(obj, indent=2)}")
    if (pew := PEW(**obj)) and pew.spec.service:
        if not pew.spec.service.enabled:
            logger.debug(f"Service not enabled for worker[{name}]!")
        elif not pew.spec.service.interfaces or len(pew.spec.service.interfaces) < 1:
            logger.debug(f"No interface is defined for worker[{name}]!")
        else:
            exposed = bool(pew.status and pew.status.worker and pew.status.worker.exposed)
            if not exposed:
                logger.debug(f"Worker[{name}] is not exposed yet!")
            endpoints = [
                {
                    "interface": interface,
                    "exposed": exposed,
                    "url": assemble_worker_endpoint_url(request=request, name=name, secured=interface.secured)
                }
                for interface in pew.spec.service.interfaces if interface.public
            ]
            return endpoints
    return []


########################################################################################################################

class PTXEdgeWorkerState(enum.StrEnum):
    READY = enum.auto()
    EXPOSED = enum.auto()
    SUCCEEDED = enum.auto()
    FAILED = enum.auto()


class K8sEventType(enum.StrEnum):
    ADDED = "ADDED"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"


class WatcherTimeout(RuntimeError):
    pass


async def watch_for_pew_resource_state(name: str,
                                       state: PTXEdgeWorkerState = PTXEdgeWorkerState.READY,
                                       timeout: int = 30,
                                       raise_for_timeout: bool = True) -> bool | None:
    async with client.ApiClient() as api_client:
        api = client.CustomObjectsApi(api_client=api_client)
        params = dict(group=PEW.group,
                      version=PEW.version,
                      namespace=CONFIG.WORKER_NS,
                      plural=PEW.plural)
        logger.info(f"Obtaining status for worker: {name}...")
        obj = await api.get_namespaced_custom_object_status(name=name, **params)
        if str2bool(obj.get('status', {}).get("worker", {}).get(state)):
            return True
        else:
            logger.debug(f"State: {state} is missing from worker[{name}]")
        async with watch.Watch() as watcher:
            logger.info(f"Watching for resource events: {name}...")
            async for event in watcher.stream(api.list_namespaced_custom_object,
                                              field_selector=f"metadata.name={name}",
                                              timeout_seconds=timeout,
                                              **params):
                _state_value = event['raw_object'].get('status', {}).get("worker", {}).get(state)
                logger.debug(f"Received event from worker[{name}]: {event['type']} - {state}: {_state_value}")
                match K8sEventType(event['type']):
                    case K8sEventType.ADDED | K8sEventType.MODIFIED:
                        if str2bool(_state_value):
                            return True
                    case K8sEventType.DELETED:
                        return False
                    case _:
                        logger.error(f"Unknown event type: {event['type']}!")
                        return None
        logger.warning(f"Watching worker[{name}] timed out...")
        if raise_for_timeout:
            raise WatcherTimeout
        return None


async def watch_for_pew_resource_deletion(name: str,
                                          timeout: int = 30,
                                          retries: int = 3,
                                          raise_for_timeout: bool = True) -> bool:
    async with client.ApiClient() as api_client:
        api = client.CustomObjectsApi(api_client=api_client)
        params = dict(group=PEW.group,
                      version=PEW.version,
                      namespace=CONFIG.WORKER_NS,
                      plural=PEW.plural)
        _start, remaining = asyncio.get_event_loop().time(), timeout
        while 0 < remaining:
            try:
                # Check for already deleted resource or deleted after watch
                logger.debug(f"Checking deletion of worker resource: {name}...")
                obj = await api.get_namespaced_custom_object_status(name=name, **params)
                logger.debug(f"{get_k8s_obj_res(obj)} is still waiting for finalization!")
            except client.ApiException as ex:
                if ex.status == fastapi.status.HTTP_404_NOT_FOUND:
                    logger.info(f"Worker resource: {name} has been deleted!")
                    return True
                else:
                    raise ex
            async with watch.Watch() as watcher:
                logger.debug(f"Watching for resource events: {name}...")
                async for event in watcher.stream(api.list_namespaced_custom_object,
                                                  field_selector=f"metadata.name={name}",
                                                  timeout_seconds=timeout // retries,
                                                  **params):
                    logger.debug(f"Received event from worker[{name}]: {event['type']}")
                    if K8sEventType(event['type']) is K8sEventType.DELETED:
                        logger.info(f"Resource: [{get_k8s_obj_res(event['raw_object'])}] has been deleted!")
                        return True
            # No deleted event received or deleted before starting watch stream
            logger.debug(f"No deletion event is received from {name}! Retrying deletion validation...")
            remaining = timeout - (asyncio.get_event_loop().time() - _start)
        if raise_for_timeout:
            raise WatcherTimeout()
        return False
