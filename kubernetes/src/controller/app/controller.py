#!/usr/bin/env python3
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
import functools
import http
import logging
import pathlib
from typing import Any

import jinja2
import jinja2.sandbox
import kopf
import yaml
from asyncer import asyncify
from kubernetes import client

from config import load_config_from_env, ENV_PREFIX
from model.ptxedgeworker import PEW, PEWSpecServiceInterface
from utils import sanitize_model, ExcludeProbesFilter, convert_k8s_api_error


########################################################################################################################

async def load_config(settings: kopf.OperatorSettings, memo: kopf.Memo, logger: kopf.Logger, **_) -> None:
    logger.info(f"Loading controller configuration...")
    # PTX-edge/controller related configurations
    # Read config items from envvars dynamically using global default values
    logger.debug(f"Loading configuration from envvars[{ENV_PREFIX}*]...")
    memo.CONFIG = load_config_from_env()
    logger.debug(f"Loaded configuration:\n" + str(memo.CONFIG.to_toml()))
    # Kopf-internal configurations
    settings.persistence.progress_storage = kopf.AnnotationsProgressStorage(prefix=PEW.group)
    settings.persistence.diffbase_storage = kopf.AnnotationsDiffBaseStorage(prefix=PEW.group,
                                                                            key='last-handled-configuration')
    settings.persistence.finalizer = f"{PEW.group}/ewt-finalizer"  # Specify own finalizer
    settings.posting.loggers = False  # No auto-creating events from logs
    logging.getLogger('kubernetes.client.rest').setLevel(logging.WARNING)  # Disable k8s client dump logs
    logging.getLogger('aiohttp.access').addFilter(ExcludeProbesFilter())  # Disable access logging


async def load_templates(memo: kopf.Memo, logger: kopf.Logger, **_) -> None:
    logger.info("Loading manifest templates...")
    memo.TEMPLATES = jinja2.sandbox.ImmutableSandboxedEnvironment(
        loader=jinja2.FileSystemLoader(pathlib.Path(__file__).parent / "templates"),
        autoescape=False,
        auto_reload=False,
        optimized=True,
        trim_blocks=True,
        lstrip_blocks=True,
        enable_async=True,
        # extensions=['jinja2.ext.do']
    )
    logger.debug(f"Loaded templates: {memo.TEMPLATES.list_templates()}")


@kopf.on.startup(errors=kopf.ErrorsMode.PERMANENT)
async def setup(settings: kopf.OperatorSettings, memo: kopf.Memo, logger: kopf.Logger, **_: Any) -> None:
    await load_config(settings=settings, memo=memo, logger=logger)
    await load_templates(logger=logger, memo=memo)


########################################################################################################################


async def _create_worker_deployment(pew: PEW, *, name: str, namespace: str, logger: kopf.Logger, memo: kopf.Memo,
                                    **_: Any):
    logger.debug("-" * 100)
    logger.info(f"Rendering worker deployment manifest...")
    template: jinja2.Template = await asyncify(memo.TEMPLATES.get_template)(name="worker_deployment.yaml.jinja2")
    manifest: str = await template.render_async(name=name, namespace=namespace, spec=pew.spec, cfg=memo.CONFIG)
    body: dict = await asyncify(yaml.safe_load)(stream=manifest)
    kopf.adopt(body, strict=True, forced=True, nested="spec.template")
    logger.debug(f"Rendered deployment object:\n{sanitize_model(body)}")
    ####
    try:
        k8s = client.AppsV1Api()
        logger.info(f"Invoke k8s {k8s.__class__.__name__}...")
        cmd_caller = asyncify(k8s.create_namespaced_deployment_with_http_info)
        obj, status, _ = await cmd_caller(namespace=namespace,
                                          body=body,
                                          field_manager=memo.CONFIG.controller.manager)
        status = http.HTTPStatus(status)
        logger.debug(f"Received response: HTTP/{status} - {status.name}")
        if not status.is_success:
            raise kopf.TemporaryError(f"Kube API response: {status}")
        logger.info(f"Created resource: {obj.kind}/{obj.metadata.name}")
    except client.ApiException as e:
        logger.error(convert_k8s_api_error(e))
        raise kopf.TemporaryError(str(e)) from e
    ###
    logger.debug("-" * 100)


async def _create_job_deployment(pew: PEW, *, name: str, namespace: str, logger: kopf.Logger, memo: kopf.Memo,
                                 **_: Any):
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
        k8s = client.BatchV1Api()
        logger.info(f"Invoke k8s {k8s.__class__.__name__}...")
        cmd_caller = asyncify(k8s.create_namespaced_job_with_http_info)
        obj, status, _ = await cmd_caller(namespace=namespace,
                                          body=body,
                                          field_manager=memo.CONFIG.controller.manager)
        status = http.HTTPStatus(status)
        logger.debug(f"Received response: HTTP/{status} - {status.name}")
        if not status.is_success:
            raise kopf.TemporaryError(f"Kube API response: {status}")
        logger.info(f"Created resource: {obj.kind}/{obj.metadata.name}")
    except client.ApiException as e:
        logger.error(convert_k8s_api_error(e))
        raise kopf.TemporaryError(str(e)) from e
    ###
    logger.debug("-" * 100)


async def _create_service(pew: PEW, template: str, *, name: str, namespace: str, logger: kopf.Logger, memo: kopf.Memo,
                          **_: Any):
    logger.debug("-" * 100)
    logger.info(f"Rendering service manifest...")
    template: jinja2.Template = await asyncify(memo.TEMPLATES.get_template)(name=template)
    manifest: str = await template.render_async(name=name,
                                                namespace=namespace,
                                                spec=pew.spec,
                                                cfg=memo.CONFIG)
    body: dict = await asyncify(yaml.safe_load)(stream=manifest)
    kopf.adopt(body, strict=True, forced=True)
    logger.debug(f"Rendered service object:\n{sanitize_model(body)}")
    ####
    try:
        k8s = client.CoreV1Api()
        logger.info(f"Invoke k8s {k8s.__class__.__name__}...")
        cmd_caller = asyncify(k8s.create_namespaced_service_with_http_info)
        obj, status, _ = await cmd_caller(namespace=namespace,
                                          body=body,
                                          field_manager=memo.CONFIG.controller.manager)
        status = http.HTTPStatus(status)
        logger.debug(f"Received response: HTTP/{status} - {status.name}")
        if not status.is_success:
            raise kopf.TemporaryError(f"Kube API response: {status}")
        logger.info(f"Created resource: {obj.kind}/{obj.metadata.name}")
    except client.ApiException as e:
        logger.error(convert_k8s_api_error(e))
        raise kopf.TemporaryError(str(e)) from e
    ###
    logger.debug("-" * 100)


async def _create_middleware(pew: PEW, *, name: str, namespace: str, logger: kopf.Logger, memo: kopf.Memo,
                             **_: Any):
    logger.debug("-" * 100)
    logger.info(f"Rendering middleware manifest...")
    template: jinja2.Template = await asyncify(memo.TEMPLATES.get_template)(name="worker_middleware.yaml.jinja2")
    manifest: str = await template.render_async(name=name,
                                                namespace=namespace,
                                                spec=pew.spec,
                                                cfg=memo.CONFIG)
    body: dict = await asyncify(yaml.safe_load)(stream=manifest)
    kopf.adopt(body, strict=False, forced=False)
    logger.debug(f"Rendered service object:\n{sanitize_model(body)}")
    ####
    try:
        k8s = client.CustomObjectsApi()
        logger.info(f"Invoke k8s {k8s.__class__.__name__}...")
        cmd_caller = asyncify(k8s.create_namespaced_custom_object_with_http_info)
        obj, status, _ = await cmd_caller(group="traefik.io",
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
    except client.ApiException as e:
        logger.error(convert_k8s_api_error(e))
        raise kopf.TemporaryError(str(e)) from e
    ###
    logger.debug("-" * 100)


async def _create_ingress(pew: PEW, *, name: str, namespace: str, logger: kopf.Logger, memo: kopf.Memo,
                          **_: Any):
    logger.debug("-" * 100)
    logger.info(f"Rendering ingress manifest...")
    template: jinja2.Template = await asyncify(memo.TEMPLATES.get_template)(name="worker_ingress.yaml.jinja2")
    manifest: str = await template.render_async(name=name,
                                                namespace=namespace,
                                                spec=pew.spec,
                                                cfg=memo.CONFIG)
    body: dict = await asyncify(yaml.safe_load)(stream=manifest)
    kopf.adopt(body, strict=False, forced=False)
    logger.debug(f"Rendered service object:\n{sanitize_model(body)}")
    ####
    try:
        k8s = client.NetworkingV1Api()
        logger.info(f"Invoke k8s {k8s.__class__.__name__}...")
        cmd_caller = asyncify(k8s.create_namespaced_ingress_with_http_info)
        obj, status, _ = await cmd_caller(namespace=namespace,
                                          body=body,
                                          field_manager=memo.CONFIG.controller.manager)
        status = http.HTTPStatus(status)
        logger.debug(f"Received response: HTTP/{status} - {status.name}")
        if not status.is_success:
            raise kopf.TemporaryError(f"Kube API response: {status}")
        logger.info(f"Created resource: {obj.kind}/{obj.metadata.name}")
    except client.ApiException as e:
        logger.error(convert_k8s_api_error(e))
        raise kopf.TemporaryError(e.reason) from e
    ###
    logger.debug("-" * 100)


########################################################################################################################

@kopf.on.create(*PEW.SELECTOR, id="worker")
async def create_ptxedgeworker(body: kopf.Body, name: str, memo: kopf.Memo, logger: kopf.Logger,
                               **_: Any) -> dict[str, Any]:
    logger.debug("=" * 100)
    ####
    if not hasattr(memo, 'model'):
        logger.info(f"Parsing {PEW.kind} model...")
        memo.model = PEW.model_validate(body, strict=False)
        logger.debug(f"Parsed model:\n{memo.model.model_dump_json(indent=2)}")
    else:
        logger.info(f"Using cached {PEW.kind} model")
    ####
    if not hasattr(memo, 'handlers'):
        memo.handlers = {}
        logger.info(f"Registering object handlers...")
        if memo.model.spec.service and memo.model.spec.service.enabled:
            memo.handlers['deployment'] = functools.partial(_create_worker_deployment,
                                                            pew=memo.model)
        else:
            memo.handlers['job'] = functools.partial(_create_job_deployment,
                                                     pew=memo.model)
        if 'PTX' in (memo.model.spec.data.src.method, memo.model.spec.worker.src.method):
            memo.handlers['builder'] = functools.partial(_create_service,
                                                         pew=memo.model,
                                                         template="builder_service.yaml.jinja2")
        if memo.model.spec.service and memo.model.spec.service.interfaces:
            if public_port := next(filter(lambda i: i.public, memo.model.spec.service.interfaces), None):
                public_port: PEWSpecServiceInterface
                memo.handlers['service'] = functools.partial(_create_service,
                                                             pew=memo.model,
                                                             template="worker_service.yaml.jinja2")
                if public_port.stripped:
                    memo.handlers['middleware'] = functools.partial(_create_middleware,
                                                                    pew=memo.model)
                memo.handlers['ingress'] = functools.partial(_create_ingress,
                                                             pew=memo.model)
        logger.debug(f"Registered sub-handlers: {[k for k in memo.handlers.keys()]}")
    else:
        logger.debug(f"Processing cached sub-handlers: {[k for k in memo.handlers.keys()]}")
    ####
    # noinspection bad-argument-type
    await kopf.execute(fns=memo.handlers)
    ####
    logger.info(f"{PEW.kind}[{name}] initiated successfully")
    kopf.info(body, reason="Initiated", message="Initiated successfully!")
    logger.debug("=" * 100)
    ###
    return {'state': 'Initiated'}
