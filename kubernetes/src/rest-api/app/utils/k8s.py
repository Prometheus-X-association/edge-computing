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
import enum
import os
import pprint
import sys
import typing

from fastapi import Query
from kubernetes_asyncio import client, config, watch

from app.model.ptxedgeworker import PEW
from app.utils.config import CONFIG
from app.utils.helper import str2bool
from app.utils.logger import logger


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


K8sLabelCollectionType = typing.Annotated[
    tuple[typing.Annotated[str, Query(pattern=r"^(.+)=(.+)$")]] | None,
    Query(examples=["tier=worker"])]


async def invoke_k8s_api(method: K8sAPIMethod,
                         body: dict[str, typing.Any] | None = None,
                         name: str | None = None,
                         label_selector: tuple[str] | None = None) -> tuple[dict[str, typing.Any], int]:
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
        logger.debug(f"Assembled request parameters:\n{pprint.pformat(params, indent=2)}")
        api_caller = getattr(api, f"{method.value}_namespaced_custom_object_with_http_info")
        obj, status, _ = await api_caller(**params)
        return obj, status


class K8sEventType(enum.StrEnum):
    ADDED = "ADDED"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"


class PTXStatusWorkerStates(enum.StrEnum):
    READY = enum.auto()
    EXPOSED = enum.auto()
    SUCCEEDED = enum.auto()
    FAILED = enum.auto()


async def watch_for_resource_state(name: str,
                                   state: PTXStatusWorkerStates = PTXStatusWorkerStates.READY,
                                   timeout: int = 30) -> bool | None:
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
            logger.debug(f"State is missing from worker[{name}]")
        async with watch.Watch() as watcher:
            logger.info(f"Watching for resource events: {name}...")
            async for event in watcher.stream(api.list_namespaced_custom_object,
                                              field_selector=f"metadata.name={name}",
                                              timeout_seconds=timeout,
                                              **params):
                _state_value = event['raw_object'].get('status', {}).get("worker", {}).get(state)
                logger.debug(f"Received event from worker[{name}]: {event['type']} - {state}: {_state_value}")
                match event['type']:
                    case K8sEventType.ADDED | K8sEventType.MODIFIED:
                        if str2bool(_state_value):
                            return True
                    case K8sEventType.DELETED:
                        return False
        logger.warning(f"Watching worker[{name}] timed out...")
        return None
