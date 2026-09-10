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
import functools
import typing

import kopf

from model.notifier import ResourceNotifier, PatchingRequestInterrupt, ResourceState
from model.ptxedgeworker import PEW, PEWSpecServiceInterface
from model.resource import (create_worker_configuration, create_builder_service, create_worker_service,
                            create_middleware, create_ingress, create_worker_deployment, create_job_deployment,
                            ResourceType)
from utils.config import load_k8s_config, load_operator_config, load_templates
from utils.helper import str2bool


########################################################################################################################

@kopf.on.startup(errors=kopf.ErrorsMode.PERMANENT)
async def setup(settings: kopf.OperatorSettings, memo: kopf.Memo, logger: kopf.Logger,
                **_: typing.Any):
    await load_k8s_config(logger=logger)
    await load_operator_config(settings=settings, memo=memo, logger=logger)
    await load_templates(logger=logger, memo=memo)


########################################################################################################################


@kopf.on.create(*PEW.SELECTOR, id="operator")
async def create_ptxedgeworker(body: kopf.Body, name: str, memo: kopf.Memo, logger: kopf.Logger,
                               **_: typing.Any):
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
            memo.handlers['config'] = functools.partial(create_worker_configuration,
                                                        pew=memo.model)
        if 'PTX' in (memo.model.spec.data.src.method, memo.model.spec.worker.src.method):
            memo.handlers['builder'] = functools.partial(create_builder_service,
                                                         pew=memo.model)
        if memo.model.spec.service and memo.model.spec.service.interfaces:
            memo.handlers['service'] = functools.partial(create_worker_service,
                                                         pew=memo.model)
            if public_port := next(filter(lambda i: i.public, memo.model.spec.service.interfaces), None):
                public_port: PEWSpecServiceInterface
                if public_port.stripped:
                    memo.handlers['middleware'] = functools.partial(create_middleware,
                                                                    pew=memo.model)
                memo.handlers['ingress'] = functools.partial(create_ingress,
                                                             pew=memo.model)
        if memo.model.spec.service and memo.model.spec.service.enabled:
            memo.handlers['deployment'] = functools.partial(create_worker_deployment,
                                                            pew=memo.model)
        else:
            memo.handlers['job'] = functools.partial(create_job_deployment,
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


########################################################################################################################

@kopf.index(*PEW.SELECTOR)
async def pew_index(name: str, memo: kopf.Memo, logger: kopf.Logger,
                    **_: typing.Any):
    if ResourceState.INDEXED in memo.get('state', []):
        return None
    memo.state = ResourceState(memo.get("state", 0)) | ResourceState.INDEXED
    logger.info(f"[INDEX] Registering state notifier...")
    return {name: ResourceNotifier()}


@kopf.daemon(*PEW.SELECTOR, cancellation_timeout=1)
async def pew_manager(name: str, pew_index: kopf.Index[str, ResourceNotifier], memo: kopf.Memo,
                      stopped: kopf.DaemonStopped, logger: kopf.Logger,
                      **_: typing.Any):
    memo.state = ResourceState(memo.get("state", 0)) | ResourceState.MANAGED
    logger.debug(f"[DAEMON] {memo.get("state")}")
    if (notif := next(iter(pew_index[name]), None)) is None:
        raise kopf.TemporaryError(f"[DAEMON] State notifier is missing from index!", delay=3)
    while not stopped:
        tasks = {
            asyncio.create_task(notif.worker.wait(), name=ResourceType.WORKER)
        }
        try:
            logger.info("[DAEMON] Waiting for notifications...")
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            logger.debug(f"[DAEMON] {done = }")
            logger.info(f"[DAEMON] Notified by {[t.get_name() for t in done]}")
            for task in done:
                if task.get_name() == ResourceType.WORKER:
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
async def watch_deployment(event: kopf.RawEvent, logger: kopf.Logger, pew_index: kopf.Index[str, ResourceNotifier],
                           **_: typing.Any):
    progressing = next((con['status'] for con in event['object']['status'].get('conditions', [])
                        if con['type'] == 'Progressing'), None)
    available = next((con['status'] for con in event['object']['status'].get('conditions', [])
                      if con['type'] == 'Available'), None)
    logger.info(f"[EVENT] Deployment {event['type']} - {progressing=}, {available=}")
    # noinspection typed-dict
    parent: str | None = next((owner.get('name') for owner in event['object']["metadata"].get('ownerReferences', [])
                               if owner.get('kind') == PEW.kind), None)
    if parent is None:
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
