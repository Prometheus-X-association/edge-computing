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
import http
import logging
import os
import pathlib
from typing import Any

import jinja2
import jinja2.sandbox
import kopf
import yaml
from asyncer import asyncify
from kubernetes import client

from model.ptxedgeworker import PEW
from utils import sanitize_model, ExcludeProbesFilter

########################################################################################################################

# Controller version
__version__ = '1.0.0'

### Globally available objects
# Required fields in the configuration
REQUIRED_FIELDS = ("temp_dir",)
# Default values of required fields using DEF_{field} names
DEF_TEMP_DIR = "templates"


########################################################################################################################

async def load_config(settings: kopf.OperatorSettings, memo: kopf.Memo, logger: kopf.Logger, **_) -> None:
    logger.info(f"Loading controller configuration...")
    # PTX-edge/controller related configurations
    # Read config items from envvars dynamically using global default values
    memo.CONFIG = {field: os.getenv(field.upper(), default=globals().get(f"DEF_{field.upper()}", None))
                   for field in REQUIRED_FIELDS}
    if not all(map(lambda _p: memo.CONFIG[_p] is not None, REQUIRED_FIELDS)):
        raise kopf.PermanentError(f"Missing one of the required configurations: {REQUIRED_FIELDS} from {memo.CONFIG}!")
    logger.debug(f"Loaded configuration: {memo.CONFIG}")
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
        loader=jinja2.FileSystemLoader(pathlib.Path(__file__).parent / memo.CONFIG["temp_dir"]),
        autoescape=False,
        auto_reload=False,
        optimized=True,
        enable_async=True)
    logger.debug(f"Loaded templates: {','.join(memo.TEMPLATES.list_templates())}")


@kopf.on.startup(errors=kopf.ErrorsMode.PERMANENT)
async def setup(settings: kopf.OperatorSettings, memo: kopf.Memo, logger: kopf.Logger, **_: Any) -> None:
    await load_config(settings=settings, memo=memo, logger=logger)
    await load_templates(logger=logger, memo=memo)


########################################################################################################################

def _is_service(spec: kopf.Spec, **_: Any) -> bool:
    return spec.get("service", {}).get("enabled", False)


@kopf.on.create(*PEW.SELECTOR, when=_is_service, id="create/service")
async def create_service(body: kopf.Body, namespace: str, logger: kopf.Logger, memo: kopf.Memo,
                         **_: Any) -> dict[str, Any]:
    logger.debug("=" * 100)
    ####
    logger.info(f"Parsing {PEW.kind} model...")
    pew = PEW.model_validate(body, strict=False)
    logger.debug(f"Parsed model:\n{pew.model_dump_json(indent=4)}")
    ####
    logger.info(f"Rendering manifest...")
    worker_temp: jinja2.Template = await asyncify(memo.TEMPLATES.get_template)(name="worker_pod.yaml.jinja2")
    manifest: str = await worker_temp.render_async(pew.spec.model_dump())
    new_body: dict = await asyncify(yaml.safe_load)(stream=manifest)
    kopf.adopt(new_body, forced=True)
    logger.debug(f"New object:\n{sanitize_model(new_body)}")
    ####
    try:
        logger.info("Invoke k8s API...")
        k8s = client.CoreV1Api()
        pod, status, _ = await asyncify(k8s.create_namespaced_pod_with_http_info)(body=new_body,
                                                                                  namespace=namespace,
                                                                                  _preload_content=True)
        logger.debug(f"Received response: HTTP/{status}")
        if (status := http.HTTPStatus(status)).is_success:
            logger.debug(f"Invocation status: {status.name}")
            kopf.info(body, reason="Starting", message=f"{PEW.__name__} {pod.metadata.name} initiated successfully!")
        else:
            raise kopf.TemporaryError(f"Kube API response: {status}")
    except client.ApiException as e:
        logger.error(f"Error received:\n{e}")
        raise kopf.TemporaryError(str(e)) from e
    logger.debug("=" * 100)
    return {'initialized': True}


@kopf.on.create(*PEW.SELECTOR, when=kopf.not_(_is_service), id="create/task")
def create_task(body: kopf.Body, namespace: str, logger: kopf.Logger, memo: kopf.Memo, **_: Any) -> dict[str, Any]:
    raise kopf.PermanentError("Not implemented yet!")
