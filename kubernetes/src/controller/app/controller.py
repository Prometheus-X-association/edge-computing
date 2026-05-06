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
import logging
import os
import pathlib
from typing import Any

import jinja2
import kopf
import yaml
from jinja2.sandbox import ImmutableSandboxedEnvironment
from kubernetes import client

from model.edgeworkertask import EWT
from utils import sanitize, ExcludeProbesFilter

########################################################################################################################

# Controller version
__version__ = '1.0.0'

### Globally available objects
# Controllers own configuration
CONFIG: dict[str, Any] = {}
# Required fields in the configuration
REQUIRED_FIELDS = ("temp_dir",)
# Default values of required fields using DEF_{field} names
DEF_TEMP_DIR = "templates"
# Environment of loaded manifest templates
TEMPLATES: jinja2.Environment


########################################################################################################################

def load_config(settings: kopf.OperatorSettings, logger: kopf.Logger) -> None:
    logger.info(f"Loading controller configuration...")
    # PTX-edge/controller related configurations
    global CONFIG
    # Read config items from envvars dynamically using global default values
    CONFIG.update({field: os.getenv(field.upper(), default=globals().get(f"DEF_{field.upper()}", None))
                   for field in REQUIRED_FIELDS})
    if not all(map(lambda _p: CONFIG[_p] is not None, REQUIRED_FIELDS)):
        raise kopf.PermanentError(f"Missing one of the required configurations: {REQUIRED_FIELDS} from {CONFIG}!")
    logger.debug(f"Loaded configuration: {CONFIG}")
    # Kopf-internal configurations
    settings.persistence.progress_storage = kopf.AnnotationsProgressStorage(prefix=EWT.group)
    settings.persistence.diffbase_storage = kopf.AnnotationsDiffBaseStorage(prefix=EWT.group,
                                                                            key='last-handled-configuration')
    settings.persistence.finalizer = f"{EWT.group}/ewt-finalizer"  # Specify own finalizer
    settings.posting.loggers = False  # No auto-creating events from logs
    logging.getLogger('kubernetes.client.rest').setLevel(logging.WARNING)  # Disable k8s client dump logs
    logging.getLogger('aiohttp.access').addFilter(ExcludeProbesFilter())  # Disable access logging


def load_templates(logger: kopf.Logger) -> None:
    logger.info("Loading manifest templates...")
    global TEMPLATES
    TEMPLATES = ImmutableSandboxedEnvironment(
        loader=jinja2.PackageLoader(package_name=pathlib.Path(__file__).stem,
                                    package_path=CONFIG["temp_dir"]),
        autoescape=False,
        auto_reload=False,
        optimized=True,
        enable_async=False)
    logger.debug(f"Loaded templates: {','.join(TEMPLATES.list_templates())}")


@kopf.on.startup()
def setup(settings: kopf.OperatorSettings, logger: kopf.Logger, **_: Any) -> None:
    load_config(settings=settings, logger=logger)
    load_templates(logger=logger)


########################################################################################################################

def is_service(spec: kopf.Spec, **_: Any) -> bool:
    return spec.get("service", {}).get("enabled", False)


@kopf.on.create(group=EWT.group, version=EWT.version, kind=EWT.kind, when=is_service, id="create")
def create_ewt_deployment(body: kopf.Body, namespace: str, logger: kopf.Logger, **_: Any) -> dict[str, Any]:
    logger.debug("=" * 100)
    logger.info(f"Parsing {EWT.__name__} model...")
    ewt = EWT.model_validate(body)
    logger.debug(f"Parsed model:\n{ewt.model_dump_json(indent=4)}")
    logger.info("Rendering application manifests...")
    worker_temp = TEMPLATES.get_template("worker_pod.yaml.j2")
    manifest = worker_temp.render(**ewt.spec.model_dump())
    logger.debug(f"Rendered pod manifest:\n{manifest}")
    logger.info("Serializing API requests...")
    _body = yaml.safe_load(manifest)
    kopf.adopt(_body, forced=True)
    logger.debug(f"Serialized request body:\n{sanitize(_body)}")
    try:
        logger.info("Invoke k8s API...")
        pod, status, _ = client.CoreV1Api().create_namespaced_pod_with_http_info(body=_body,
                                                                                 namespace=namespace,
                                                                                 _preload_content=True)
        logger.debug(f"Invocation result: HTTP:{status}\n{sanitize(pod)}")
        kopf.info(body, reason="Starting", message=f"{EWT.__name__} {pod.metadata.name} initiated successfully!")
    except client.ApiException as e:
        logger.error(f"Error received:\n{e}")
        raise kopf.TemporaryError(str(e)) from e
    logger.debug("=" * 100)
    return {'finished': True}  # will be the new status


@kopf.on.create(group=EWT.group, version=EWT.version, kind=EWT.kind, when=kopf.not_(is_service), id="create")
def create_ewt_job(body: kopf.Body, namespace: str, logger: kopf.Logger, **_: Any) -> dict[str, Any]:
    raise kopf.PermanentError("Not implemented yet!")
