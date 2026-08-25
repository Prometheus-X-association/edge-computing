# Copyright 2025 Janos Czentye
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
import contextlib
import http
import json
import os
import pathlib
import sys
import typing

import fastapi
import urllib3
from asyncify import asyncify
from kubernetes import client, config

from app import __version__
from app.config import ApiConfiguration
from app.logger import logger, convert_k8s_api_error
from app.model.ptxedgeworker import PEW
from app.model.responses import PTXEdgeWorkerStatus, PTXEdgeWorkerResponse
from app.model.versions import VersionsResponse

########################################################################################################################

CONFIG = ApiConfiguration()


async def setup_k8s_client():
    try:
        logger.debug("Loading in-cluster K8s configuration....")
        config.load_incluster_config()
    except config.ConfigException as e:
        logger.error(f"Error loading Kubernetes API config:\n{e}")
        sys.exit(os.EX_CONFIG)


@contextlib.asynccontextmanager
async def lifespan(_app: fastapi.FastAPI):
    logger.info("Starting PTX Edge Computing REST-API...")
    await setup_k8s_client()
    yield
    logger.info("Stopping PTX Edge Computing REST-API...")


app = fastapi.FastAPI(title="PTX Edge Computing REST-API",
                      description="The Edge Computing (Decentralized AI processing) BB-02 provides value-added "
                                  "services exploiting an underlying distributed edge computing infrastructure.",
                      # contact=dict(email="czentye.janos@vik.bme.hu"),
                      license_info=dict(name="Apache 2.0",
                                        url="https://www.apache.org/licenses/LICENSE-2.0.html"),
                      version=__version__,
                      root_path=CONFIG.ROOT_PATH,
                      servers=[dict(url=CONFIG.ROOT_PATH,
                                    description="PTX Edge Computing")],
                      openapi_tags=[dict(name="customerAPI",
                                         description="Customer-facing API (EdgeAPI)",
                                         external_docs=dict(
                                             description="Prometheus-X",
                                             url="https://github.com/Prometheus-X-association/edge-computing"),
                                         )],
                      docs_url="/ui/",
                      redoc_url=None,
                      lifespan=lifespan)


########################################################################################################################

@app.get("/versions", status_code=http.HTTPStatus.OK)
@app.head("/versions", status_code=http.HTTPStatus.OK)
async def get_versions() -> VersionsResponse:
    """Versions of the REST-API component"""
    return VersionsResponse(api=__version__, framework=fastapi.__version__)


@app.get("/health")
@app.head("/health")
async def health():
    """For health check purposes"""
    return fastapi.responses.Response(status_code=http.HTTPStatus.OK)


########################################################################################################################

@app.put("/workers/{worker_name}", response_model=PTXEdgeWorkerResponse, status_code=http.HTTPStatus.CREATED)
async def create_worker(worker_name: str, pew: PEW) -> typing.Any:
    """Create PTX Edge Computing worker"""
    logger.info(f"Received {PEW.__name__} create request with name: {worker_name}")
    logger.debug("=" * 100)
    logger.debug(f"Parsed model:\n{pew.model_dump_json(indent=2)}")
    logger.debug("Creating manifest body...")
    manifest = {
        'apiVersion': f"{PEW.group}/{PEW.version}",
        'kind': PEW.kind,
        'metadata': {
            'name': worker_name,
            'namespace': CONFIG.WORKER_NS,
            'labels': {
                'tier': 'worker'
            }
        }
    }
    sanitized_request_body = pew.model_dump(mode="json",
                                            context=dict(expose_secrets=True),
                                            exclude={"status"},
                                            exclude_unset=True,
                                            exclude_none=True,
                                            warnings=True)
    manifest.update(sanitized_request_body)
    response = {}
    try:
        k8s = client.CustomObjectsApi()
        logger.info(f"Invoke k8s {k8s.__class__.__name__}...")
        create_cmd = asyncify(k8s.create_namespaced_custom_object_with_http_info)
        obj, _status, _ = await create_cmd(group=PEW.group,
                                           version=PEW.version,
                                           namespace=CONFIG.WORKER_NS,
                                           plural=PEW.plural,
                                           body=manifest)
        result = http.HTTPStatus(_status)
        logger.debug(f"Received response: HTTP/{result} - {result.name}")
        if not result.is_success:
            logger.error(result)
            raise fastapi.HTTPException(status_code=_status,
                                        detail={"status": PTXEdgeWorkerStatus.ERROR,
                                                "code": _status,
                                                "resource": {
                                                    "name": obj.metadata.name,
                                                    "group": obj.group,
                                                    "kind": obj.kind,
                                                }})
        logger.info(f"Created resource: {obj.get('kind')}/{obj.get('metadata', {}).get('name')}")
    except client.ApiException as e:
        logger.error(convert_k8s_api_error(e))
        error = json.loads(str(e.body))
        code = http.HTTPStatus.CONFLICT if e.reason == "Conflict" else http.HTTPStatus.UNPROCESSABLE_ENTITY
        raise fastapi.HTTPException(status_code=code,
                                    detail={"status": PTXEdgeWorkerStatus.ERROR,
                                            "reason": e.reason,
                                            "message": error['message'],
                                            "resource": error['details']
                                            })
    except urllib3.exceptions.MaxRetryError as e:
        logger.error(f"Max retries exceeded: {e}")
        raise fastapi.HTTPException(status_code=http.HTTPStatus.FAILED_DEPENDENCY,
                                    detail={"status": PTXEdgeWorkerStatus.ERROR,
                                            "reason": str(e.reason)})
    logger.debug("=" * 100)
    return {"status": PTXEdgeWorkerStatus.INITIALIZED}


########################################################################################################################


if __name__ == '__main__':
    # Automatic reloading for development purposed,
    # In other case use `fastapi dev --host localhost --port 8080 --reload app/main.py`
    # or `fastapi run --port 8080 --workers $((`nproc` * 2)) app/main.py`
    # or `gunicorn -k uvicorn_worker.UvicornWorker -b :8080 -w $((`nproc` * 2)) --access-logfile=- main:app`
    # http://localhost:8080/docs | http://localhost:8080/redoc
    import uvicorn

    uvicorn.run(f"{pathlib.Path(__file__).stem}:app", host='127.0.0.1', port=9999,
                reload=True, access_log=True, log_level="debug")
