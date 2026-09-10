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

import jinja2
import kopf
import yaml
from asyncer import asyncify
from kubernetes.aio import client

from model.ptxedgeworker import PEW, PEWStatusOperatorItem, PEWStatusOperatorItemResult
from utils.helper import sanitize_model, convert_k8s_api_error


async def create_worker_configuration(pew: PEW, *, name: str, namespace: str, logger: kopf.Logger, memo: kopf.Memo,
                                      **_: typing.Any):
    logger.debug("-" * 100)
    logger.info(f"Rendering worker configuration manifest...")
    template: jinja2.Template = await asyncify(memo.TEMPLATES.get_template)(name="worker_configmap.yaml.jinja2")
    manifest: str = await template.render_async(name=name, namespace=namespace, spec=pew.spec, cfg=memo.CONFIG)
    body: dict = await asyncify(yaml.safe_load)(stream=manifest)
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
    logger.debug("-" * 100)


async def create_worker_deployment(pew: PEW, *, name: str, namespace: str, memo: kopf.Memo, patch: kopf.Patch,
                                   logger: kopf.Logger, **_: typing.Any):
    logger.debug("-" * 100)
    logger.info(f"Rendering worker deployment manifest...")
    template: jinja2.Template = await asyncify(memo.TEMPLATES.get_template)(name="worker_deployment.yaml.jinja2")
    manifest: str = await template.render_async(name=name, namespace=namespace, spec=pew.spec, cfg=memo.CONFIG)
    body: dict = await asyncify(yaml.safe_load)(stream=manifest)
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
        PEWStatusOperatorItem(handler="",
                              result=PEWStatusOperatorItemResult.SUCCESS).model_dump(mode="json")
    ]
    logger.debug("-" * 100)


async def create_job_deployment(pew: PEW, *, name: str, namespace: str, logger: kopf.Logger, memo: kopf.Memo,
                                **_: typing.Any):
    logger.debug("-" * 100)
    logger.info(f"Rendering worker job manifest...")
    template: jinja2.Template = await asyncify(memo.TEMPLATES.get_template)(name="worker_job.yaml.jinja2")
    manifest: str = await template.render_async(name=name,
                                                namespace=namespace,
                                                spec=pew.spec,
                                                cfg=memo.CONFIG)
    body: dict = await asyncify(yaml.safe_load)(stream=manifest)
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
    logger.debug("-" * 100)


async def __create_service(pew: PEW, template: str, *, name: str, namespace: str, forced_name: bool = True,
                           logger: kopf.Logger, memo: kopf.Memo):
    template: jinja2.Template = await asyncify(memo.TEMPLATES.get_template)(name=template)
    manifest: str = await template.render_async(name=name,
                                                namespace=namespace,
                                                spec=pew.spec,
                                                cfg=memo.CONFIG)
    body: dict = await asyncify(yaml.safe_load)(stream=manifest)
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


async def create_builder_service(pew: PEW, *, name: str, namespace: str, logger: kopf.Logger, memo: kopf.Memo,
                                 **_: typing.Any):
    logger.debug("-" * 100)
    logger.info(f"Rendering builder webhook manifest...")
    await __create_service(pew, "builder_service.yaml.jinja2", forced_name=False,
                           name=name, namespace=namespace, logger=logger, memo=memo)
    ###
    logger.debug("-" * 100)


async def create_worker_service(pew: PEW, *, name: str, namespace: str, logger: kopf.Logger, memo: kopf.Memo,
                                **_: typing.Any):
    logger.debug("-" * 100)
    logger.info(f"Rendering worker service manifest...")
    await __create_service(pew, "worker_service.yaml.jinja2", forced_name=True,
                           name=name, namespace=namespace, logger=logger, memo=memo)
    ###
    logger.debug("-" * 100)


async def create_middleware(pew: PEW, *, name: str, namespace: str, logger: kopf.Logger, memo: kopf.Memo,
                            **_: typing.Any):
    logger.debug("-" * 100)
    logger.info(f"Rendering middleware manifest...")
    template: jinja2.Template = await asyncify(memo.TEMPLATES.get_template)(name="worker_middleware.yaml.jinja2")
    manifest: str = await template.render_async(name=name,
                                                namespace=namespace,
                                                spec=pew.spec,
                                                cfg=memo.CONFIG)
    body: dict = await asyncify(yaml.safe_load)(stream=manifest)
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
    logger.debug("-" * 100)


async def create_ingress(pew: PEW, *, name: str, namespace: str, logger: kopf.Logger, memo: kopf.Memo,
                         **_: typing.Any):
    logger.debug("-" * 100)
    logger.info(f"Rendering ingress manifest...")
    template: jinja2.Template = await asyncify(memo.TEMPLATES.get_template)(name="worker_ingress.yaml.jinja2")
    manifest: str = await template.render_async(name=name,
                                                namespace=namespace,
                                                spec=pew.spec,
                                                cfg=memo.CONFIG)
    body: dict = await asyncify(yaml.safe_load)(stream=manifest)
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
    logger.debug("-" * 100)


########################################################################################################################

class ResourceType(enum.StrEnum):
    WORKER = enum.auto()


# RESOURCE_FACTORY = {
#
# }
#
#
# async def create_resource()
