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
import asyncio
import enum
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
from kubernetes.aio import client, config

from model.notifier import ResourceNotifier, NotifierTask, PatchingRequestInterrupt
from model.ptxedgeworker import PEW, PEWSpecServiceInterface, PEWStatusOperator, PEWStatusOperatorState
from utils.config import load_config_from_env, ENV_PREFIX
from utils.utils import sanitize_model, ExcludeProbesFilter, convert_k8s_api_error, str2bool


########################################################################################################################

async def load_k8s_config(logger: kopf.Logger, **_):
    logger.info("Loading k8s in-cluster config...")
    config.load_incluster_config()


async def load_operator_config(settings: kopf.OperatorSettings, memo: kopf.Memo, logger: kopf.Logger, **_):
    logger.info(f"Loading operator configuration...")
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
    logging.getLogger('aiohttp.access').addFilter(ExcludeProbesFilter())  # Disable access logging
    logging.getLogger('kubernetes.aio.client.rest').setLevel(logging.WARNING)  # Disable k8s client dump logs


async def load_templates(memo: kopf.Memo, logger: kopf.Logger, **_):
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
    await load_k8s_config(logger=logger)
    await load_operator_config(settings=settings, memo=memo, logger=logger)
    await load_templates(logger=logger, memo=memo)


########################################################################################################################

async def _create_worker_configuration(pew: PEW, *, name: str, namespace: str, logger: kopf.Logger, memo: kopf.Memo,
                                       **_: Any):
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


async def _create_builder_service(pew: PEW, *, name: str, namespace: str, logger: kopf.Logger, memo: kopf.Memo,
                                  **_: Any):
    logger.debug("-" * 100)
    logger.info(f"Rendering builder webhook manifest...")
    await __create_service(pew, "builder_service.yaml.jinja2", forced_name=False,
                           name=name, namespace=namespace, logger=logger, memo=memo)
    ###
    logger.debug("-" * 100)


async def _create_worker_service(pew: PEW, *, name: str, namespace: str,
                                 logger: kopf.Logger, memo: kopf.Memo, **_: Any):
    logger.debug("-" * 100)
    logger.info(f"Rendering worker service manifest...")
    await __create_service(pew, "worker_service.yaml.jinja2", forced_name=True,
                           name=name, namespace=namespace, logger=logger, memo=memo)
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

@kopf.on.create(*PEW.SELECTOR, id="operator")
async def create_ptxedgeworker(body: kopf.Body, name: str, memo: kopf.Memo, logger: kopf.Logger,
                               **_: Any) -> dict[str, Any]:
    logger.debug("=" * 100)
    ####
    if "model" not in memo:
        logger.info(f"Parsing {PEW.kind} model...")
        memo.model = PEW.model_validate(body, strict=False)
        logger.debug(f"Parsed model:\n{memo.model.model_dump_json(indent=2)}")
    else:
        logger.info(f"Using cached {PEW.kind} model")
    ####
    if 'handlers' not in memo:
        memo.handlers = {}
        logger.info(f"Registering object handlers...")
        if memo.model.spec.worker.config and memo.model.spec.worker.config.file:
            memo.handlers['config'] = functools.partial(_create_worker_configuration,
                                                        pew=memo.model)
        if 'PTX' in (memo.model.spec.data.src.method, memo.model.spec.worker.src.method):
            memo.handlers['builder'] = functools.partial(_create_builder_service,
                                                         pew=memo.model)
        if memo.model.spec.service and memo.model.spec.service.interfaces:
            memo.handlers['service'] = functools.partial(_create_worker_service,
                                                         pew=memo.model)
            if public_port := next(filter(lambda i: i.public, memo.model.spec.service.interfaces), None):
                public_port: PEWSpecServiceInterface
                if public_port.stripped:
                    memo.handlers['middleware'] = functools.partial(_create_middleware,
                                                                    pew=memo.model)
                memo.handlers['ingress'] = functools.partial(_create_ingress,
                                                             pew=memo.model)
        if memo.model.spec.service and memo.model.spec.service.enabled:
            memo.handlers['deployment'] = functools.partial(_create_worker_deployment,
                                                            pew=memo.model)
        else:
            memo.handlers['job'] = functools.partial(_create_job_deployment,
                                                     pew=memo.model)
        logger.debug(f"Registered sub-handlers: {[k for k in memo.handlers.keys()]}")
    else:
        logger.debug(f"Processing cached sub-handlers: {[k for k in memo.handlers.keys()]}")
    ####
    await kopf.execute(fns=memo.handlers)
    ####
    del memo.handlers
    logger.info(f"{PEW.kind}[{name}] initiated successfully")
    memo.state = ResourceState(memo.get("state", 0)) | ResourceState.CREATED
    logger.debug(f"[HANDLER] {memo.state}")
    kopf.info(body, reason="Initiated", message="Initiated successfully!")
    logger.debug("=" * 100)
    ###
    return PEWStatusOperator(state=PEWStatusOperatorState.FINISHED).model_dump(mode="json", exclude_none=True)


class ResourceState(enum.Flag):
    INDEXED = enum.auto()
    MANAGED = enum.auto()
    CREATED = enum.auto()


@kopf.index(*PEW.SELECTOR)
async def pew_index(name: str, memo: kopf.Memo, logger: kopf.Logger, **_: Any):
    if ResourceState.INDEXED in memo.get('state', []):
        return None
    memo.state = ResourceState(memo.get("state", 0)) | ResourceState.INDEXED
    logger.info(f"[INDEX] Registering state notifier...")
    return {name: ResourceNotifier()}


@kopf.daemon(*PEW.SELECTOR, cancellation_timeout=1)
async def pew_manager(name: str, pew_index: kopf.Index, memo: kopf.Memo, stopped: kopf.DaemonStopped,
                      patch: kopf.Patch, logger: kopf.Logger, **_: Any):
    memo.state = ResourceState(memo.get("state", 0)) | ResourceState.MANAGED
    logger.debug(f"[DAEMON] {memo.get("state")}")
    if (notif := next(iter(pew_index[name]), None)) is None:
        raise kopf.TemporaryError(f"[DAEMON] State notifier is missing from index!", delay=3)
    while not stopped:
        tasks = {
            asyncio.create_task(notif.worker.wait(), name=NotifierTask.WORKER)
        }
        try:
            logger.info("[DAEMON] Waiting for notifications...")
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            logger.debug(f"[DAEMON] {done = }")
            logger.info(f"[DAEMON] Notified by {[t.get_name() for t in done]}")
            for task in done:
                if task.get_name() == NotifierTask.WORKER:
                    notif.worker.clear()
                    logger.info("[DAEMON] Updating resource status...")
                    # patch.status['available'] = True
                    raise PatchingRequestInterrupt
            for t in pending:
                t.cancel()
        except asyncio.CancelledError:
            logger.info(f"[DAEMON] State notifier cancelled!")
            for t in tasks:
                t.cancel()
    memo.state &= ~ResourceState.MANAGED


@kopf.on.event('apps', 'v1', 'deployments', field="status", value=kopf.PRESENT,
               labels={"app.kubernetes.io/component": "worker"})
async def watch_deployment(event: kopf.RawEvent, logger: kopf.Logger, pew_index: kopf.Index, **_: Any):
    progressing = next((con['status'] for con in event['object']['status'].get('conditions', [])
                        if con['type'] == 'Progressing'), None)
    available = next((con['status'] for con in event['object']['status'].get('conditions', [])
                      if con['type'] == 'Available'), None)
    logger.info(f"[EVENT] Deployment {event['type']} - {progressing=}, {available=}")
    parent = next((owner.get('name') for owner in event['object']["metadata"].get('ownerReferences', [])
                   if owner.get('kind') == PEW.kind), None)
    if not parent:
        raise kopf.PermanentError("[EVENT] Owner reference is missing from Deployment!")
    elif parent not in pew_index:
        if event['type'] == 'DELETED':
            logger.debug(f"[EVENT] Deployment's owner[{parent}] has been already deleted!")
            return
        raise kopf.TemporaryError(f"[EVENT] Deployment's owner[{parent}] is missing from index!", delay=3)
    if all(map(str2bool, (progressing, available))):
        logger.info("[EVENT] Deployment got available!")
        if (notif := next(iter(pew_index[parent]), None)) is not None:
            notif.worker.set()

########################################################################################################################
