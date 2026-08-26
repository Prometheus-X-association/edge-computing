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
import contextlib
import pprint
import typing

import fastapi
import kubernetes
import urllib3

from app import __version__
from app.model.errors import (raise_for_k8s_error, raise_for_failed_k8s_request, raise_for_network_error,
                              PTXEdgeAPIError)
from app.model.ptxedgeworker import PEW
from app.model.responses import (PTXEdgeWorkerResponseStatus, PTXEdgeWorkerResponse, VersionsResponse,
                                 PTXEdgeWorkerCollectionResponse)
from app.utils.config import CONFIG
from app.utils.k8s import setup_k8s_client, invoke_k8s_api, K8sAPIMethod
from app.utils.logger import logger


########################################################################################################################

@contextlib.asynccontextmanager
async def lifespan(_app: fastapi.FastAPI):
    logger.info("Starting PTX Edge Computing REST-API...")
    logger.debug(f"Used configuration:\n{CONFIG.model_dump_json(indent=2)}")
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
                      openapi_tags=[dict(name="Customer",
                                         description="Customer-facing API (EdgeAPI)",
                                         external_docs=dict(
                                             description="Prometheus-X",
                                             url="https://github.com/Prometheus-X-association/edge-computing")),
                                    dict(name="Internal",
                                         description="Internal management API"),
                                    dict(name="Cluster",
                                         description="Cluster-wide management API")],
                      docs_url="/ui/",
                      redoc_url=None,
                      lifespan=lifespan)


########################################################################################################################

@app.get("/version",
         tags=["Internal"],
         response_model=VersionsResponse,
         status_code=fastapi.status.HTTP_200_OK)
@app.head("/version",
          tags=["Internal"],
          response_model=VersionsResponse,
          status_code=fastapi.status.HTTP_200_OK)
async def get_versions() -> VersionsResponse:
    """Versions of the REST-API component"""
    return VersionsResponse()


@app.get("/health",
         tags=["Internal"],
         status_code=fastapi.status.HTTP_200_OK)
@app.head("/health",
          tags=["Internal"],
          status_code=fastapi.status.HTTP_200_OK)
async def health() -> None:
    """For health check purposes"""
    pass


########################################################################################################################


async def _create_pew_worker(pew: PEW, name: str | None = None) -> dict[str, typing.Any] | None:
    """Create PTX Edge Computing worker"""
    logger.info(f"Received {PEW.__name__} create request with name: {name}")
    logger.debug("=" * 100)
    logger.debug(f"Parsed model:\n{pew.model_dump_json(indent=2)}")
    logger.debug("Creating manifest body...")
    manifest: dict[str, typing.Any] = {
        'apiVersion': f"{PEW.group}/{PEW.version}",
        'kind': PEW.kind,
        'metadata': {
            'namespace': CONFIG.WORKER_NS,
            'labels': {
                'tier': 'worker'
            }
        }
    }
    if name:
        manifest['metadata']['name'] = name
    else:
        manifest['metadata']['generateName'] = "worker-"
    manifest.update(pew.model_dump(mode="json",
                                   context=dict(expose_secrets=True),
                                   exclude={"status"},
                                   exclude_unset=True,
                                   exclude_none=True,
                                   warnings=True))
    try:
        obj, _status = await invoke_k8s_api(method=K8sAPIMethod.CREATE,
                                            body=manifest)
        raise_for_k8s_error(obj=obj, status=_status)
        logger.info(f"Created resource: {obj['kind']}/{obj['metadata']['name']}")
        logger.debug(f"Obtained response:\n{pprint.pformat(obj, indent=2)}")
        logger.debug("=" * 100)
        grp, ver = obj['apiVersion'].split('/', maxsplit=1)
        return {"status": PTXEdgeWorkerResponseStatus.INITIALIZED,
                "resource": {
                    "name": obj['metadata']['name'],
                    "kind": obj['kind'],
                    "group": grp,
                    "version": ver
                }}
    except kubernetes.client.ApiException as e:
        raise_for_failed_k8s_request(e)
    except urllib3.exceptions.MaxRetryError as e:
        raise_for_network_error(e)


@app.get("/workers/{name}",
         tags=["Customer"],
         responses={
             fastapi.status.HTTP_404_NOT_FOUND: {"model": PTXEdgeAPIError},
             fastapi.status.HTTP_424_FAILED_DEPENDENCY: {"model": PTXEdgeAPIError}},
         response_model=PEW,
         response_model_exclude_unset=True,
         response_model_exclude_none=True,
         status_code=fastapi.status.HTTP_200_OK)
async def get_worker_by_name(name: typing.Annotated[str, fastapi.Path(pattern=r"^[a-zA-Z0-9_-]+$")]):
    """Obtain deployed PTX-Edge worker with given name"""
    logger.info(f"Received {PEW.__name__} get request with name: {name}")
    logger.debug("=" * 100)
    try:
        obj, _status = await invoke_k8s_api(method=K8sAPIMethod.GET,
                                            name=name)
        raise_for_k8s_error(obj=obj, status=_status)
        logger.info(f"Obtained resource: {obj['apiVersion']}/{obj['metadata']['name']}")
        logger.debug(f"Obtained response:\n{pprint.pformat(obj, indent=2)}")
        logger.debug("=" * 100)
        return obj
    except kubernetes.client.ApiException as e:
        raise_for_failed_k8s_request(e)
    except urllib3.exceptions.MaxRetryError as e:
        raise_for_network_error(e)


@app.put("/workers/{name}",
         tags=["Customer"],
         responses={
             fastapi.status.HTTP_406_NOT_ACCEPTABLE: {"model": PTXEdgeAPIError},
             fastapi.status.HTTP_409_CONFLICT: {"model": PTXEdgeAPIError},
             fastapi.status.HTTP_424_FAILED_DEPENDENCY: {"model": PTXEdgeAPIError}},
         response_model=PTXEdgeWorkerResponse,
         status_code=fastapi.status.HTTP_201_CREATED)
async def create_worker_with_name(name: typing.Annotated[str, fastapi.Path(pattern=r"^[a-zA-Z0-9_-]+$")],
                                  pew: typing.Annotated[PEW, fastapi.Body]):
    """Create PTX-Edge worker with given name"""
    return await _create_pew_worker(pew=pew, name=name)


@app.post("/workers",
          tags=["Customer"],
          responses={
              fastapi.status.HTTP_406_NOT_ACCEPTABLE: {"model": PTXEdgeAPIError},
              fastapi.status.HTTP_424_FAILED_DEPENDENCY: {"model": PTXEdgeAPIError}},
          response_model=PTXEdgeWorkerResponse,
          status_code=fastapi.status.HTTP_201_CREATED)
async def create_worker(pew: typing.Annotated[PEW, fastapi.Body]):
    """Create PTX-Edge worker with autogenerated name"""
    return await _create_pew_worker(pew=pew)


@app.delete("/workers/{name}",
            tags=["Customer"],
            responses={
                fastapi.status.HTTP_404_NOT_FOUND: {"model": PTXEdgeAPIError},
                fastapi.status.HTTP_424_FAILED_DEPENDENCY: {"model": PTXEdgeAPIError}},
            response_model=PTXEdgeWorkerResponse,
            status_code=fastapi.status.HTTP_200_OK)
async def delete_worker_by_name(name: typing.Annotated[str, fastapi.Path(pattern=r"^[a-zA-Z0-9_-]+$")]):
    """Delete PTX-Edge worker with given name"""
    logger.info(f"Received {PEW.__name__} delete request with name: {name}")
    logger.debug("=" * 100)
    try:
        obj, _status = await invoke_k8s_api(method=K8sAPIMethod.DELETE,
                                            name=name)
        raise_for_k8s_error(obj=obj, status=_status)
        logger.info(f"Deleted resource: {obj['details']['kind']}/{obj['details']['name']}")
        logger.debug(f"Obtained response:\n{pprint.pformat(obj, indent=2)}")
        logger.debug("=" * 100)
        return {"status": PTXEdgeWorkerResponseStatus.TERMINATING,
                "resource": {
                    "name": obj['details']['name'],
                    "group": obj['details']['group'],
                    "kind": obj['details']['kind']
                }}
    except kubernetes.client.ApiException as e:
        raise_for_failed_k8s_request(e)
    except urllib3.exceptions.MaxRetryError as e:
        raise_for_network_error(e)


########################################################################################################################
@app.get("/workers",
         tags=["Cluster"],
         responses={
             fastapi.status.HTTP_424_FAILED_DEPENDENCY: {"model": PTXEdgeAPIError}},
         response_model=PTXEdgeWorkerCollectionResponse,
         response_model_exclude_unset=True,
         response_model_exclude_none=True,
         status_code=fastapi.status.HTTP_200_OK)
async def list_all_workers(resource: bool = False):
    """Obtain deployed PTX-Edge workers"""
    logger.info(f"Received {PEW.__name__} list request")
    logger.debug("=" * 100)
    try:
        obj, _status = await invoke_k8s_api(method=K8sAPIMethod.LIST)
        raise_for_k8s_error(obj=obj, status=_status)
        logger.info(f"Obtained resource: {obj['apiVersion']}/{obj['kind']} with size: {len(obj.get("items", []))}")
        logger.debug(f"Obtained response:\n{pprint.pformat(obj, indent=2)}")
        logger.debug("=" * 100)
        ret = {"workers": [{"name": w['metadata']['name'],
                            "state": w.get('status', {}).get('worker', {}).get('state')}
                           for w in obj.get("items", [])]}
        if resource:
            ret.update({"resources": obj.get("items", [])})
        return ret
    except kubernetes.client.ApiException as e:
        raise_for_failed_k8s_request(e)
    except urllib3.exceptions.MaxRetryError as e:
        raise_for_network_error(e)


@app.delete("/workers",
            tags=["Cluster"],
            responses={
                fastapi.status.HTTP_424_FAILED_DEPENDENCY: {"model": PTXEdgeAPIError}},
            response_model=PTXEdgeWorkerCollectionResponse,
            response_model_exclude_unset=True,
            response_model_exclude_none=True,
            status_code=fastapi.status.HTTP_200_OK)
async def delete_all_workers(resource: bool = False):
    """Delete all deployed PTX-Edge workers"""
    logger.info(f"Received {PEW.__name__} delete all request")
    logger.debug("=" * 100)
    try:
        obj, _status = await invoke_k8s_api(method=K8sAPIMethod.DELETE_ALL)
        raise_for_k8s_error(obj=obj, status=_status)
        logger.info(f"Obtained resource: {obj['apiVersion']}/{obj['kind']} with size: {len(obj.get("items", []))}")
        logger.debug(f"Obtained response:\n{pprint.pformat(obj, indent=2)}")
        logger.debug("=" * 100)
        ret = {"workers": [{"name": w['metadata']['name']}
                           for w in obj.get("items", [])]}
        if resource:
            ret.update({"resources": obj.get("items", [])})
        return ret
    except kubernetes.client.ApiException as e:
        raise_for_failed_k8s_request(e)
    except urllib3.exceptions.MaxRetryError as e:
        raise_for_network_error(e)


########################################################################################################################


if __name__ == '__main__':
    # Automatic reloading for development purposed,
    # In other case use `fastapi dev --host localhost --port 8080 --reload app/main.py`
    # or `fastapi run --port 8080 --workers $((`nproc` * 2)) app/main.py`
    # or `gunicorn -k uvicorn_worker.UvicornWorker -b :8080 -w $((`nproc` * 2)) --access-logfile=- main:app`
    # http://localhost:8080/docs | http://localhost:8080/redoc
    import uvicorn
    import pathlib

    uvicorn.run(f"{pathlib.Path(__file__).stem}:app", host='127.0.0.1', port=9999,
                reload=True, access_log=True, log_level="debug")
