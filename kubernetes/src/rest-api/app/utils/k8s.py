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
import sys
import typing

from asyncify import asyncify
from kubernetes import config, client

from app.model.ptxedgeworker import PEW
from app.utils.config import CONFIG
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


async def invoke_k8s_api(method: K8sAPIMethod,
                         body: dict[str, typing.Any] | None = None,
                         name: str | None = None) -> tuple[dict[str, typing.Any], int]:
    k8s = client.CustomObjectsApi()
    logger.info(f"Invoke k8s {k8s.__class__.__name__}...")
    api_caller = asyncify(getattr(k8s, f"{method.value}_namespaced_custom_object_with_http_info"))
    params = dict(group=PEW.group, version=PEW.version, namespace=CONFIG.WORKER_NS, plural=PEW.plural)
    if method is K8sAPIMethod.CREATE:
        params['field_manager'] = CONFIG.field_manager
    if body is not None:
        params["body"] = body
    if name is not None:
        params["name"] = name
    obj, status, _ = await api_caller(**params)
    return obj, status
