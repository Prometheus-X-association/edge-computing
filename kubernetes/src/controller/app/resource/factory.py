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
import http
import typing

import kopf
import yaml
from asyncer import asyncify
from kubernetes.aio import client

from model.ptxedgeworker import PEW, PEWStatusOperatorItem, PEWStatusOperatorItemResult
from utils.helper import sanitize_model, convert_k8s_api_error


########################################################################################################################

class ResourceType(enum.StrEnum):
    CONFIG = enum.auto()
    BUILDER = enum.auto()
    SERVICE = enum.auto()
    MIDDLEWARE = enum.auto()
    INGRESS = enum.auto()
    DEPLOYMENT = enum.auto()
    JOB = enum.auto()


TEMPLATE_FACTORY = {
    ResourceType.CONFIG: "worker_configmap.yaml.jinja2",
    ResourceType.BUILDER: "builder_service.yaml.jinja2",
    ResourceType.SERVICE: "worker_service.yaml.jinja2",
    ResourceType.MIDDLEWARE: "worker_middleware.yaml.jinja2",
    ResourceType.INGRESS: "worker_ingress.yaml.jinja2",
    ResourceType.DEPLOYMENT: "worker_deployment.yaml.jinja2",
    ResourceType.JOB: "worker_job.yaml.jinja2"
}


async def render_template(_type: ResourceType,
                          pew: PEW, name: str, namespace: str, memo: kopf.Memo) -> dict[str, typing.Any]:
    template = await asyncify(memo.TEMPLATES.get_template)(name=TEMPLATE_FACTORY[_type])
    manifest = await template.render_async(name=name, namespace=namespace, spec=pew.spec, cfg=memo.CONFIG)
    body = await asyncify(yaml.safe_load)(stream=manifest)
    return body


########################################################################################################################

async def create_worker_configuration(pew: PEW, *, name: str, namespace: str, memo: kopf.Memo, patch: kopf.Patch,
                                      logger: kopf.Logger, **_: typing.Any):
    logger.debug("-" * 100)
    logger.info(f"Rendering worker configuration manifest...")
    body: dict[str, typing.Any] = await render_template(ResourceType.CONFIG,
                                                        pew=pew, name=name, namespace=namespace, memo=memo)
    kopf.adopt(body, strict=True, forced=True, nested="spec.template")
    logger.debug(f"Rendered configuration object:\n{sanitize_model(body)}")
    ####
    try:
        async with client.ApiClient() as api_client:
            api = client.CoreV1Api(api_client=api_client)
            logger.info(f"Invoke k8s {api.__class__.__name__}...")
            # noinspection unresolved-references
            obj, status, _ = await api.create_namespaced_config_map_with_http_info(
                namespace=namespace,
                body=body,
                field_manager=memo.CONFIG.controller.manager)
            status = http.HTTPStatus(status)
            logger.debug(f"Received response: HTTP/{status} - {status.name}")
            if not status.is_success:
                raise kopf.TemporaryError(f"Kube API response: {status}")
            logger.info(f"Created resource: {obj.kind}/{obj.metadata.name}")
    except client.ApiException as ex:
        logger.error(convert_k8s_api_error(ex))
        raise kopf.TemporaryError(str(ex)) from ex
    ###
    patch.status["operator"] = [
        PEWStatusOperatorItem(handler=ResourceType.CONFIG,
                              result=PEWStatusOperatorItemResult.SUCCESS).model_dump(mode="json")
    ]
    ###
    logger.debug("-" * 100)


async def create_worker_deployment(pew: PEW, *, name: str, namespace: str, memo: kopf.Memo, patch: kopf.Patch,
                                   logger: kopf.Logger, **_: typing.Any):
    logger.debug("-" * 100)
    logger.info(f"Rendering worker deployment manifest...")
    body: dict[str, typing.Any] = await render_template(ResourceType.DEPLOYMENT,
                                                        pew=pew, name=name, namespace=namespace, memo=memo)
    kopf.adopt(body, strict=True, forced=True, nested="spec.template")
    logger.debug(f"Rendered deployment object:\n{sanitize_model(body)}")
    ####
    try:
        async with client.ApiClient() as api_client:
            api = client.AppsV1Api(api_client=api_client)
            logger.info(f"Invoke k8s {api.__class__.__name__}...")
            # noinspection unresolved-references
            obj, status, _ = await api.create_namespaced_deployment_with_http_info(
                namespace=namespace,
                body=body,
                field_manager=memo.CONFIG.controller.manager)
            status = http.HTTPStatus(status)
            logger.debug(f"Received response: HTTP/{status} - {status.name}")
            if not status.is_success:
                raise kopf.TemporaryError(f"Kube API response: {status}")
            logger.info(f"Created resource: {obj.kind}/{obj.metadata.name}")
    except client.ApiException as ex:
        logger.error(convert_k8s_api_error(ex))
        raise kopf.TemporaryError(str(ex)) from ex
    ###
    patch.status["operator"] = [
        PEWStatusOperatorItem(handler=ResourceType.DEPLOYMENT,
                              result=PEWStatusOperatorItemResult.SUCCESS).model_dump(mode="json")
    ]
    ###
    logger.debug("-" * 100)


async def create_worker_job(pew: PEW, *, name: str, namespace: str, memo: kopf.Memo, patch: kopf.Patch,
                            logger: kopf.Logger, **_: typing.Any):
    logger.debug("-" * 100)
    logger.info(f"Rendering worker job manifest...")
    body: dict[str, typing.Any] = await render_template(ResourceType.JOB,
                                                        pew=pew, name=name, namespace=namespace, memo=memo)
    kopf.adopt(body, strict=True, forced=True, nested="spec.template")
    logger.debug(f"Rendered deployment object:\n{sanitize_model(body)}")
    ####
    try:
        async with client.ApiClient() as api_client:
            api = client.BatchV1Api(api_client=api_client)
            logger.info(f"Invoke k8s {api.__class__.__name__}...")
            # noinspection unresolved-references
            obj, status, _ = await api.create_namespaced_job_with_http_info(
                namespace=namespace,
                body=body,
                field_manager=memo.CONFIG.controller.manager)
            status = http.HTTPStatus(status)
            logger.debug(f"Received response: HTTP/{status} - {status.name}")
            if not status.is_success:
                raise kopf.TemporaryError(f"Kube API response: {status}")
            logger.info(f"Created resource: {obj.kind}/{obj.metadata.name}")
    except client.ApiException as ex:
        logger.error(convert_k8s_api_error(ex))
        raise kopf.TemporaryError(str(ex)) from ex
    ###
    patch.status["operator"] = [
        PEWStatusOperatorItem(handler=ResourceType.JOB,
                              result=PEWStatusOperatorItemResult.SUCCESS).model_dump(mode="json")
    ]
    ###
    logger.debug("-" * 100)


async def _create_service(pew: PEW, _type: ResourceType, *, name: str, namespace: str, forced_name: bool = True,
                          logger: kopf.Logger, memo: kopf.Memo):
    body: dict[str, typing.Any] = await render_template(_type,
                                                        pew=pew, name=name, namespace=namespace, memo=memo)
    kopf.adopt(body, strict=True, forced=forced_name)
    logger.debug(f"Rendered service object:\n{sanitize_model(body)}")
    ####
    try:
        async with client.ApiClient() as api_client:
            api = client.CoreV1Api(api_client=api_client)
            logger.info(f"Invoke k8s {api.__class__.__name__}...")
            # noinspection unresolved-references
            obj, status, _ = await api.create_namespaced_service_with_http_info(
                namespace=namespace,
                body=body,
                field_manager=memo.CONFIG.controller.manager)
            status = http.HTTPStatus(status)
            logger.debug(f"Received response: HTTP/{status} - {status.name}")
            if not status.is_success:
                raise kopf.TemporaryError(f"Kube API response: {status}")
            logger.info(f"Created resource: {obj.kind}/{obj.metadata.name}")
    except client.ApiException as ex:
        logger.error(convert_k8s_api_error(ex))
        raise kopf.TemporaryError(str(ex)) from ex


async def create_builder_service(pew: PEW, *, name: str, namespace: str, memo: kopf.Memo, patch: kopf.Patch,
                                 logger: kopf.Logger, **_: typing.Any):
    logger.debug("-" * 100)
    logger.info(f"Rendering builder webhook manifest...")
    await _create_service(pew, ResourceType.BUILDER, forced_name=False,
                          name=name, namespace=namespace, logger=logger, memo=memo)
    ###
    patch.status["operator"] = [
        PEWStatusOperatorItem(handler=ResourceType.BUILDER,
                              result=PEWStatusOperatorItemResult.SUCCESS).model_dump(mode="json")
    ]
    ###
    logger.debug("-" * 100)


async def create_worker_service(pew: PEW, *, name: str, namespace: str, memo: kopf.Memo, patch: kopf.Patch,
                                logger: kopf.Logger, **_: typing.Any):
    logger.debug("-" * 100)
    logger.info(f"Rendering worker service manifest...")
    await _create_service(pew, ResourceType.SERVICE, forced_name=True,
                          name=name, namespace=namespace, logger=logger, memo=memo)
    ###
    patch.status["operator"] = [
        PEWStatusOperatorItem(handler=ResourceType.SERVICE,
                              result=PEWStatusOperatorItemResult.SUCCESS).model_dump(mode="json")
    ]
    ###
    logger.debug("-" * 100)


async def create_middleware(pew: PEW, *, name: str, namespace: str, memo: kopf.Memo, patch: kopf.Patch,
                            logger: kopf.Logger, **_: typing.Any):
    logger.debug("-" * 100)
    logger.info(f"Rendering middleware manifest...")
    body: dict[str, typing.Any] = await render_template(ResourceType.MIDDLEWARE,
                                                        pew=pew, name=name, namespace=namespace, memo=memo)
    kopf.adopt(body, strict=True, forced=False)
    logger.debug(f"Rendered service object:\n{sanitize_model(body)}")
    ####
    try:
        async with client.ApiClient() as api_client:
            api = client.CustomObjectsApi(api_client=api_client)
            logger.info(f"Invoke k8s {api.__class__.__name__}...")
            # noinspection unresolved-references
            obj, status, _ = await api.create_namespaced_custom_object_with_http_info(
                group="traefik.io",
                version="v1alpha1",
                namespace=namespace,
                plural="middlewares",
                body=body,
                field_manager=memo.CONFIG.controller.manager)
            status = http.HTTPStatus(status)
            logger.debug(f"Received response: HTTP/{status} - {status.name}")
            if not status.is_success:
                raise kopf.TemporaryError(f"Kube API response: {status}")
            logger.info(f"Created resource: {obj.get('kind')}/{obj.get('metadata', {}).get('name')}")
    except client.ApiException as ex:
        logger.error(convert_k8s_api_error(ex))
        raise kopf.TemporaryError(str(ex)) from ex
    ###
    patch.status["operator"] = [
        PEWStatusOperatorItem(handler=ResourceType.MIDDLEWARE,
                              result=PEWStatusOperatorItemResult.SUCCESS).model_dump(mode="json")
    ]
    ###
    logger.debug("-" * 100)


async def create_ingress(pew: PEW, *, name: str, namespace: str, memo: kopf.Memo, patch: kopf.Patch,
                         logger: kopf.Logger, **_: typing.Any):
    logger.debug("-" * 100)
    logger.info(f"Rendering ingress manifest...")
    body: dict[str, typing.Any] = await render_template(ResourceType.INGRESS,
                                                        pew=pew, name=name, namespace=namespace, memo=memo)
    kopf.adopt(body, strict=True, forced=False)
    logger.debug(f"Rendered service object:\n{sanitize_model(body)}")
    ####
    try:
        async with client.ApiClient() as api_client:
            api = client.NetworkingV1Api(api_client=api_client)
            logger.info(f"Invoke k8s {api.__class__.__name__}...")
            # noinspection unresolved-references
            obj, status, _ = await api.create_namespaced_ingress_with_http_info(
                namespace=namespace,
                body=body,
                field_manager=memo.CONFIG.controller.manager)
            status = http.HTTPStatus(status)
            logger.debug(f"Received response: HTTP/{status} - {status.name}")
            if not status.is_success:
                raise kopf.TemporaryError(f"Kube API response: {status}")
            logger.info(f"Created resource: {obj.kind}/{obj.metadata.name}")
    except client.ApiException as ex:
        logger.error(convert_k8s_api_error(ex))
        raise kopf.TemporaryError(ex.reason) from ex
    ###
    patch.status["operator"] = [
        PEWStatusOperatorItem(handler=ResourceType.INGRESS,
                              result=PEWStatusOperatorItemResult.SUCCESS).model_dump(mode="json")
    ]
    ###
    logger.debug("-" * 100)


########################################################################################################################

RESOURCE_FACTORY = {
    ResourceType.CONFIG: create_worker_configuration,
    ResourceType.BUILDER: create_builder_service,
    ResourceType.SERVICE: create_worker_service,
    ResourceType.MIDDLEWARE: create_middleware,
    ResourceType.INGRESS: create_ingress,
    ResourceType.DEPLOYMENT: create_worker_deployment,
    ResourceType.JOB: create_worker_job,
}


def load_and_create(_type: ResourceType) -> typing.Callable:
    return RESOURCE_FACTORY[_type]
