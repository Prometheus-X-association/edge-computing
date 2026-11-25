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
import hashlib
import json
import pprint
import typing
from typing import Any

import aiohttp
import fastapi
import pydantic
import urllib3
from fastapi import BackgroundTasks
from kubernetes_asyncio import client

from app import __version__
from app.handlers import (watch_for_worker_status, create_pew_worker, list_all_incluster_workers,
                          delete_all_incluster_workers, create_workers_batch, list_all_incluster_worker_endpoints,
                          assemble_worker_endpoints, collect_worker_node_zones)
from app.model.adapters import (PTXServiceChainInfraRequest, PTXServiceChainInfraResponse, PTXServiceChainInfraHeaders,
                                PTXServiceChainResumeCallback, PTXServiceChainAsyncResponse)
from app.model.errors import (PTXEdgeAPIError, raise_for_k8s_error, raise_for_failed_k8s_request,
                              raise_for_network_error)
from app.model.ptxedgeworker import PEW, PEWStatus
from app.model.responses import (PTXEdgeWorkerResponseState, PTXEdgeWorkerResponse, VersionsResponse,
                                 PTXEdgeWorkerCollectionResponse, PTXEdgeWorkerCollectionResponseStatus,
                                 PTXEdgeWorkerNameType, PTXEdgeWorkerEndpoint, PTXWorkerBatchId,
                                 PTXEdgeWorkerBatchResponse, PTXEdgeWorkerNodeResponse)
from app.utils.config import CONFIG
from app.utils.helper import (cancel_on_disconnect, get_k8s_obj_res, validate_pews_list)
from app.utils.k8s import (setup_k8s_client, invoke_k8s_pew_api, K8sAPIMethod, K8sLabelCollectionType,
                           PTXEdgeWorkerState, watch_for_pew_resource_deletion)
from app.utils.logger import logger, sanitize_model


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
                      # redirect_slashes=False,
                      openapi_tags=[dict(name="Edge-Worker",
                                         description="Customer-facing API (EdgeAPI)",
                                         external_docs=dict(
                                             description="Prometheus-X",
                                             url="https://github.com/Prometheus-X-association/edge-computing")),
                                    dict(name="Worker-Batch",
                                         description="Batch-based Worker API"),
                                    dict(name="Adapter",
                                         description="Service chain adapter API"),
                                    dict(name="Cluster",
                                         description="Cluster-wide management API"),
                                    dict(name="Internal",
                                         description="Internal management API")],
                      docs_url="/ui",
                      redoc_url=None,
                      lifespan=lifespan,
                      ignore_trailing_slash=True)


########################################################################################################################

@app.get("/version",
         tags=["Internal"],
         response_model=VersionsResponse,
         summary="Version info",
         status_code=fastapi.status.HTTP_200_OK)
async def get_versions() -> VersionsResponse:
    """Versions of the REST-API component"""
    return VersionsResponse()


@app.get("/health",
         tags=["Internal"],
         summary="Status endpoint",
         status_code=fastapi.status.HTTP_200_OK)
@app.head("/health",
          tags=["Internal"],
          summary="Status endpoint",
          status_code=fastapi.status.HTTP_200_OK)
async def health() -> None:
    """For health check purposes"""
    pass


########################################################################################################################


@app.get("/workers/{name}",
         tags=["Edge-Worker"],
         responses={
             fastapi.status.HTTP_404_NOT_FOUND: {"model": PTXEdgeAPIError},
             fastapi.status.HTTP_502_BAD_GATEWAY: {"model": PTXEdgeAPIError}
         },
         response_model=PEW,
         response_model_exclude_unset=True,
         response_model_exclude_none=True,
         summary="Obtain the worker with the given name",
         status_code=fastapi.status.HTTP_200_OK)
async def get_worker_by_name(name: PTXEdgeWorkerNameType):
    """Obtain deployed PTX-Edge worker with given name"""
    logger.debug("=" * 100)
    logger.info(f"Received {PEW.__name__} get request with name: {name}")
    try:
        obj, _status = await invoke_k8s_pew_api(method=K8sAPIMethod.GET,
                                                name=name)
        raise_for_k8s_error(obj=obj, status=_status)
        obj.pop("status", None)
        logger.info(f"Obtained resource: {get_k8s_obj_res(obj)}")
        logger.debug(f"Assembled response body:\n{sanitize_model(obj, indent=2)}")
        logger.debug("=" * 100)
        return obj
    except client.ApiException as ex:
        raise_for_failed_k8s_request(ex)
    except (aiohttp.ClientError, urllib3.exceptions.MaxRetryError) as ex:
        raise_for_network_error(ex)


@app.get("/workers/{name}/status",
         tags=["Edge-Worker"],
         responses={
             fastapi.status.HTTP_404_NOT_FOUND: {"model": PTXEdgeAPIError},
             fastapi.status.HTTP_502_BAD_GATEWAY: {"model": PTXEdgeAPIError}
         },
         response_model=PEWStatus,
         response_model_exclude_unset=True,
         response_model_exclude_none=True,
         summary="Obtain the worker's status with the given name",
         status_code=fastapi.status.HTTP_200_OK)
async def get_worker_status(name: PTXEdgeWorkerNameType):
    """Obtain deployed PTX-Edge worker with given name"""
    logger.debug("=" * 100)
    logger.info(f"Received {PEW.__name__} status request with name: {name}")
    try:
        obj, _status = await invoke_k8s_pew_api(method=K8sAPIMethod.GET,
                                                name=name,
                                                status=True)
        raise_for_k8s_error(obj=obj, status=_status)
        status = obj.get("status", {})
        logger.info(f"Obtained resource: {get_k8s_obj_res(obj)}")
        logger.debug(f"Assembled response body:\n{sanitize_model(status, indent=2)}")
        logger.debug("=" * 100)
        return status
    except client.ApiException as ex:
        raise_for_failed_k8s_request(ex)
    except (aiohttp.ClientError, urllib3.exceptions.MaxRetryError) as ex:
        raise_for_network_error(ex)


@app.get("/workers/{name}/endpoints",
         tags=["Edge-Worker"],
         responses={
             fastapi.status.HTTP_404_NOT_FOUND: {"model": PTXEdgeAPIError},
             fastapi.status.HTTP_502_BAD_GATEWAY: {"model": PTXEdgeAPIError}
         },
         response_model=list[PTXEdgeWorkerEndpoint],
         response_model_exclude_unset=True,
         response_model_exclude_none=True,
         summary="Obtain the worker's endpoints with the given name",
         status_code=fastapi.status.HTTP_200_OK)
async def get_worker_endpoints(request: fastapi.Request, name: PTXEdgeWorkerNameType):
    """Obtain deployed PTX-Edge worker with given name"""
    logger.debug("=" * 100)
    logger.info(f"Received {PEW.__name__} status request with name: {name}")
    try:
        endpoints = await assemble_worker_endpoints(request=request, name=name)
        logger.debug(f"Assembled response body:\n{pprint.pformat(endpoints, sort_dicts=False)}")
        logger.debug("=" * 100)
        return endpoints
    except client.ApiException as ex:
        raise_for_failed_k8s_request(ex)
    except (aiohttp.ClientError, urllib3.exceptions.MaxRetryError) as ex:
        raise_for_network_error(ex)


@app.get("/workers/{name}/node",
         tags=["Edge-Worker"],
         responses={
             fastapi.status.HTTP_404_NOT_FOUND: {"model": PTXEdgeAPIError},
             fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": PTXEdgeAPIError},
             fastapi.status.HTTP_502_BAD_GATEWAY: {"model": PTXEdgeAPIError}
         },
         response_model=PTXEdgeWorkerNodeResponse,
         response_model_exclude_unset=True,
         response_model_exclude_none=True,
         summary="Obtain the privacy zones on which the worker with the given name is deployed",
         status_code=fastapi.status.HTTP_200_OK)
async def get_worker_node_zones(name: PTXEdgeWorkerNameType):
    """Obtain deployed PTX-Edge worker with given name"""
    logger.debug("=" * 100)
    logger.info(f"Received {PEW.__name__} node zones request")
    response = await collect_worker_node_zones(name=name)
    logger.debug(f"Assembled response body:\n{sanitize_model(response, indent=2)}")
    logger.debug("=" * 100)
    return response


@app.get("/workers/{name}/watcher",
         tags=["Edge-Worker"],
         responses={
             fastapi.status.HTTP_404_NOT_FOUND: {"model": PTXEdgeAPIError},
             fastapi.status.HTTP_502_BAD_GATEWAY: {"model": PTXEdgeAPIError}
         },
         response_model=PTXEdgeWorkerCollectionResponseStatus,
         response_model_exclude_unset=True,
         response_model_exclude_none=True,
         summary="Watch a worker's condition to be fulfilled",
         status_code=fastapi.status.HTTP_200_OK)
async def get_worker_status_watcher(request: fastapi.Request,
                                    name: PTXEdgeWorkerNameType,
                                    state: typing.Annotated[
                                        PTXEdgeWorkerState, fastapi.Query(description="Watched worker state")
                                    ] = PTXEdgeWorkerState.READY,
                                    timeout: typing.Annotated[int, fastapi.Query(gt=0)] = 30):
    """Obtain deployed PTX-Edge worker with given name"""
    logger.debug("=" * 100)
    logger.info(f"Received {PEW.__name__} resource watch request")
    response = await watch_for_worker_status(request=request, name=name, state=state, timeout=timeout)
    logger.debug(f"Assembled response body:\n{pprint.pformat(response, sort_dicts=False)}")
    logger.debug("=" * 100)
    return response


########################################################################################################################

@app.post("/workers",
          tags=["Edge-Worker"],
          responses={
              fastapi.status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": PTXEdgeAPIError},
              fastapi.status.HTTP_409_CONFLICT: {"model": PTXEdgeAPIError},
              fastapi.status.HTTP_502_BAD_GATEWAY: {"model": PTXEdgeAPIError}
          },
          response_model=PTXEdgeWorkerResponse,
          response_model_exclude_none=True,
          summary="Create a new worker",
          status_code=fastapi.status.HTTP_201_CREATED)
async def post_new_worker(request: fastapi.Request,
                          pew: typing.Annotated[PEW, fastapi.Body],
                          label: K8sLabelCollectionType = None):
    """Create PTX-Edge worker with an autogenerated or implicitly-defined name"""
    logger.debug("=" * 100)
    logger.info(f"Received {PEW.__name__} create request")
    if pew.spec.name:
        logger.info(f"Using resource defined name: {pew.spec.name}")
    response = await create_pew_worker(request=request, pew=pew, name=pew.spec.name, labels=label)
    logger.debug(f"Assembled response body:\n{pprint.pformat(response, sort_dicts=False)}")
    logger.debug("=" * 100)
    return response


@app.delete("/workers/{name}",
            tags=["Edge-Worker"],
            responses={
                fastapi.status.HTTP_404_NOT_FOUND: {"model": PTXEdgeAPIError},
                fastapi.status.HTTP_502_BAD_GATEWAY: {"model": PTXEdgeAPIError}
            },
            response_model=PTXEdgeWorkerResponse,
            response_model_exclude_unset=True,
            response_model_exclude_none=True,
            summary="Delete worker with the given name",
            status_code=fastapi.status.HTTP_200_OK)
async def delete_worker_by_name(name: PTXEdgeWorkerNameType,
                                tolerance: typing.Annotated[int, fastapi.Query(description="Grace period", ge=1)] = 10,
                                wait: typing.Annotated[
                                    bool, fastapi.Query(description="Should wait for complete deletion")] = False):
    """Delete PTX-Edge worker with given name"""
    logger.debug("=" * 100)
    logger.info(f"Received {PEW.__name__} delete request with name: {name}")
    try:
        obj, _status = await invoke_k8s_pew_api(method=K8sAPIMethod.DELETE,
                                                name=name,
                                                body=client.V1DeleteOptions(
                                                    propagation_policy="Foreground" if wait else "Background",
                                                    grace_period_seconds=tolerance).to_dict())
        raise_for_k8s_error(obj=obj, status=_status)
        pprint.pprint(obj, indent=2)
        logger.info(f"Deleted resource: {get_k8s_obj_res(obj)}")
        logger.debug(f"Obtained response:\n{sanitize_model(obj, indent=2)}")
        response = {
            "state": PTXEdgeWorkerResponseState.DELETED if wait else PTXEdgeWorkerResponseState.TERMINATING,
            "resource": {
                "name": obj['metadata']['name'] if 'metadata' in obj else obj['details']['name'],
                "group": obj['apiVersion'] if 'apiVersion' in obj else obj['details']['group'],
                "kind": obj['kind'] if 'kind' in obj else obj['details']['kind']
            }
        }
        logger.debug(f"Assembled response body:\n{pprint.pformat(response, sort_dicts=False)}")
        logger.debug("=" * 100)
        return response
    except client.ApiException as ex:
        raise_for_failed_k8s_request(ex)
    except (aiohttp.ClientError, urllib3.exceptions.MaxRetryError) as ex:
        raise_for_network_error(ex)


@app.put("/workers/{name}",
         tags=["Edge-Worker"],
         responses={
             fastapi.status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": PTXEdgeAPIError},
             fastapi.status.HTTP_502_BAD_GATEWAY: {"model": PTXEdgeAPIError}
         },
         response_model=PTXEdgeWorkerResponse,
         response_model_exclude_none=True,
         summary="Create/recreate the worker with the given name",
         status_code=fastapi.status.HTTP_201_CREATED)
async def put_worker_by_name(request: fastapi.Request,
                             name: PTXEdgeWorkerNameType,
                             pew: typing.Annotated[PEW, fastapi.Body],
                             label: K8sLabelCollectionType = None,
                             tolerance: typing.Annotated[
                                 int, fastapi.Query(description="Grace period", ge=1)] = 10):
    """Re-create PTX-Edge worker with given name"""
    logger.debug("=" * 100)
    logger.info(f"Received {PEW.__name__} re-create request with name: {name}")
    if pew.spec.name and pew.spec.name != name:
        logger.warning(f"Resource defines name: {pew.spec.name} different from <name> parameter: {name}!")
    try:
        obj, _status = await invoke_k8s_pew_api(method=K8sAPIMethod.DELETE,
                                                name=name,
                                                body=client.V1DeleteOptions(
                                                    propagation_policy="Foreground",
                                                    grace_period_seconds=tolerance).to_dict())
        raise_for_k8s_error(obj=obj, status=_status)
        logger.info(f"Deleted resource: {get_k8s_obj_res(obj)}")
        logger.debug(f"Obtained response:\n{sanitize_model(obj, indent=2)}")
        try:
            async with cancel_on_disconnect(request=request, logger=logger, raise_for_disconnect=False):
                logger.info("Waiting for dependent resources to remove finalizers...")
                _result = await watch_for_pew_resource_deletion(name=name,
                                                                timeout=tolerance,
                                                                retry_interval=3,
                                                                raise_for_timeout=False)
                logger.debug(f"Deletion confirmed: {_result}")
        except* Exception as exg:
            for ex in exg.exceptions:
                raise ex
    except client.ApiException as ex:
        if ex.body:
            error = json.loads(ex.body.decode() if isinstance(ex.body, bytes) else str(ex.body))
        else:
            error = {}
        if int(error.get('code', 0)) == fastapi.status.HTTP_404_NOT_FOUND:
            logger.info(f"Worker[{name}] is not found! Skip deletion step.")
        else:
            raise_for_failed_k8s_request(ex)
    except (aiohttp.ClientError, urllib3.exceptions.MaxRetryError) as ex:
        raise_for_network_error(ex)
    response = await create_pew_worker(request=request, pew=pew, name=name, labels=label)
    logger.debug(f"Assembled response body:\n{pprint.pformat(response, sort_dicts=False)}")
    logger.debug("=" * 100)
    return response


########################################################################################################################

@app.get("/cluster/workers",
         tags=["Cluster"],
         responses={
             fastapi.status.HTTP_502_BAD_GATEWAY: {"model": PTXEdgeAPIError}
         },
         response_model=PTXEdgeWorkerCollectionResponse,
         response_model_exclude_unset=True,
         response_model_exclude_none=True,
         summary="List all workers in the cluster",
         status_code=fastapi.status.HTTP_200_OK)
async def get_all_workers(resource: typing.Annotated[bool, fastapi.Query()] = False,
                          label: K8sLabelCollectionType = None):
    """Obtain deployed PTX-Edge worker states and resources filtered by optional labels"""
    logger.debug("=" * 100)
    logger.info(f"Received {PEW.__name__} list request with labels: {label}")
    response = await list_all_incluster_workers(resource=resource, label=label)
    logger.debug(f"Assembled response body:\n{pprint.pformat(response, sort_dicts=False)}")
    logger.debug("=" * 100)
    return response


@app.get("/cluster/workers/endpoints",
         tags=["Cluster"],
         responses={
             fastapi.status.HTTP_502_BAD_GATEWAY: {"model": PTXEdgeAPIError}
         },
         response_model=list[PTXEdgeWorkerEndpoint],
         response_model_exclude_unset=True,
         response_model_exclude_none=True,
         summary="List all worker endpoints in the cluster",
         status_code=fastapi.status.HTTP_200_OK)
async def get_all_worker_endpoints(request: fastapi.Request,
                                   label: K8sLabelCollectionType = None):
    """Obtain endpoints of PTX-Edge workers deployed in a given batch"""
    logger.debug("=" * 100)
    logger.info(f"Received {PEW.__name__} list endpoints request with labels: {label}")
    response = await list_all_incluster_worker_endpoints(request=request, label=label)
    logger.debug(f"Assembled response body:\n{pprint.pformat(response, sort_dicts=False)}")
    logger.debug("=" * 100)
    return response


@app.delete("/cluster/workers",
            tags=["Cluster"],
            responses={
                fastapi.status.HTTP_502_BAD_GATEWAY: {"model": PTXEdgeAPIError}
            },
            response_model=PTXEdgeWorkerCollectionResponse,
            response_model_exclude_unset=True,
            response_model_exclude_none=True,
            summary="Delete all workers from the cluster",
            status_code=fastapi.status.HTTP_200_OK)
async def delete_all_workers(resource: typing.Annotated[bool, fastapi.Query()] = False,
                             label: K8sLabelCollectionType = None,
                             tolerance: typing.Annotated[int, fastapi.Query(description="Grace period", ge=1)] = 10,
                             wait: typing.Annotated[
                                 bool, fastapi.Query(description="Should wait for complete deletion")] = False):
    """Delete deployed PTX-Edge workers filtered by optional labels"""
    logger.debug("=" * 100)
    logger.info(f"Received {PEW.__name__} delete request with labels: {label}")
    response = await delete_all_incluster_workers(resource=resource, label=label, tolerance=tolerance, wait=wait)
    logger.debug(f"Assembled response body:\n{pprint.pformat(response, sort_dicts=False)}")
    logger.debug("=" * 100)
    return response


########################################################################################################################

@app.post("/workers/batch",
          tags=["Worker-Batch"],
          responses={
              fastapi.status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": PTXEdgeAPIError},
              fastapi.status.HTTP_409_CONFLICT: {"model": PTXEdgeAPIError},
              fastapi.status.HTTP_502_BAD_GATEWAY: {"model": PTXEdgeAPIError}
          },
          response_model=PTXEdgeWorkerBatchResponse,
          response_model_exclude_none=True,
          summary="Create workers in a batch",
          status_code=fastapi.status.HTTP_201_CREATED)
async def post_workers_in_batch(request: fastapi.Request,
                                pews: typing.Annotated[list[PEW], pydantic.AfterValidator(validate_pews_list)],
                                parallel: typing.Annotated[bool, fastapi.Query] = False,
                                wait: typing.Annotated[bool, fastapi.Query] = False,
                                rollback: typing.Annotated[bool, fastapi.Query] = True,
                                timeout: typing.Annotated[int, fastapi.Query(gt=0)] = 30,
                                label: K8sLabelCollectionType = None) -> dict[str, str | list[dict[str, Any]]]:
    """Create batch of named PTX-Edge workers"""
    logger.debug("=" * 100)
    logger.info(f"Received {PEW.__name__} batch create request")
    logger.debug(f"Parsed resource names: {[p.spec.name for p in pews]}")
    batch_id = hashlib.sha256('\n'.join(p.model_dump_json(indent=None,
                                                          ensure_ascii=True,
                                                          exclude_none=True,
                                                          exclude_unset=True)
                                        for p in pews).encode('ascii')).hexdigest()[:16]
    logger.debug(f"Generated batch id: {batch_id}")
    if label is None:
        label = [f"ptxedgeworkers.dataspace.ptx.org/batch={batch_id}"]
    else:
        label.append(f"ptxedgeworkers.dataspace.ptx.org/batch={batch_id}")
    responses = await create_workers_batch(request=request,
                                           pews=pews,
                                           parallel=parallel,
                                           wait=wait,
                                           rollback=rollback,
                                           timeout=timeout,
                                           label=label)
    logger.debug(f"Assembled response body:\n{pprint.pformat(responses, sort_dicts=False)}")
    logger.debug("=" * 100)
    return {"batch_id": batch_id, "workers": responses}


@app.get("/workers/batch/{id}",
         tags=["Worker-Batch"],
         responses={
             fastapi.status.HTTP_502_BAD_GATEWAY: {"model": PTXEdgeAPIError}
         },
         response_model=PTXEdgeWorkerCollectionResponse,
         response_model_exclude_unset=True,
         response_model_exclude_none=True,
         summary="List workers in a batch with a given id",
         status_code=fastapi.status.HTTP_200_OK)
async def get_all_workers_in_batch(id: PTXWorkerBatchId,
                                   resource: typing.Annotated[bool, fastapi.Query()] = False):
    """Obtain states and resources of a PTX-Edge worker batch"""
    return await get_all_workers(resource=resource,
                                 label=[f"ptxedgeworkers.dataspace.ptx.org/batch={id}"])


@app.get("/workers/batch/{id}/endpoints",
         tags=["Worker-Batch"],
         responses={
             fastapi.status.HTTP_502_BAD_GATEWAY: {"model": PTXEdgeAPIError}
         },
         response_model=list[PTXEdgeWorkerEndpoint],
         response_model_exclude_unset=True,
         response_model_exclude_none=True,
         summary="List all endpoints in a batch with the given name",
         status_code=fastapi.status.HTTP_200_OK)
async def get_all_worker_endpoint_in_batch(request: fastapi.Request,
                                           id: PTXWorkerBatchId):
    """Obtain endpoints of PTX-Edge workers deployed in a given batch"""
    logger.debug("=" * 100)
    logger.info(f"Received {PEW.__name__} batch list endpoints request")
    response = await list_all_incluster_worker_endpoints(request=request,
                                                         label=[f"ptxedgeworkers.dataspace.ptx.org/batch={id}"])
    logger.debug(f"Assembled response body:\n{pprint.pformat(response, sort_dicts=False)}")
    logger.debug("=" * 100)
    return response


@app.delete("/workers/batch/{id}",
            tags=["Worker-Batch"],
            responses={
                fastapi.status.HTTP_502_BAD_GATEWAY: {"model": PTXEdgeAPIError}
            },
            response_model=PTXEdgeWorkerCollectionResponse,
            response_model_exclude_unset=True,
            response_model_exclude_none=True,
            summary="Delete workers in a batch with the given name",
            status_code=fastapi.status.HTTP_200_OK)
async def delete_all_workers_in_batch(id: PTXWorkerBatchId,
                                      resource: typing.Annotated[bool, fastapi.Query()] = False,
                                      tolerance: typing.Annotated[
                                          int, fastapi.Query(description="Grace period", ge=1)] = 10,
                                      wait: typing.Annotated[
                                          bool, fastapi.Query(
                                              description="Should wait for complete deletion")] = False):
    """Delete PTX-Edge workers deployed in a batch"""
    return await delete_all_workers(resource=resource,
                                    tolerance=tolerance,
                                    wait=wait,
                                    label=[f"ptxedgeworkers.dataspace.ptx.org/batch={id}"])


########################################################################################################################


@app.post("/adapters/infra",
          tags=["Adapter"],
          responses={
              fastapi.status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": PTXEdgeAPIError},
              fastapi.status.HTTP_409_CONFLICT: {"model": PTXEdgeAPIError},
              fastapi.status.HTTP_502_BAD_GATEWAY: {"model": PTXEdgeAPIError}
          },
          response_model=PTXServiceChainInfraResponse,
          summary="Create worker batch synchronously via PDC",
          status_code=fastapi.status.HTTP_201_CREATED)
async def post_workers_as_sync_infra_service(request: fastapi.Request,
                                             body: typing.Annotated[PTXServiceChainInfraRequest, fastapi.Body()],
                                             label: K8sLabelCollectionType = None):
    """Infrastructure service endpoint for creating worker batch synchronously by Service Chain Adapter"""
    logger.debug("=" * 100)
    logger.info("Received Infrastructure Service sync invocation request")
    logger.debug(f"Parsed resource names: {[p.spec.name for p in body.data]}")
    label = body.params.get("label", label) if isinstance(body.params, dict) else None
    logger.info(f"Worker execution mode: wait=False, parallel=False, {label=}")
    worker_status = await create_workers_batch(request=request,
                                               pews=body.data,
                                               parallel=False,
                                               wait=False,
                                               label=label)
    response = {
        "contract": body.contract,
        "data": worker_status,
        "params": body.params
    }
    logger.debug(f"Assembled response body:\n{pprint.pformat(response, sort_dicts=False)}")
    logger.debug("=" * 100)
    return response


@app.post("/adapters/infra/tasks",
          tags=["Adapter"],
          responses={
              fastapi.status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": PTXEdgeAPIError},
              fastapi.status.HTTP_409_CONFLICT: {"model": PTXEdgeAPIError},
              fastapi.status.HTTP_502_BAD_GATEWAY: {"model": PTXEdgeAPIError}
          },
          response_model=PTXServiceChainAsyncResponse,
          summary="Create worker batch asynchronously via PDC",
          status_code=fastapi.status.HTTP_202_ACCEPTED)
async def post_workers_as_async_infra_service(request: fastapi.Request,
                                              body: typing.Annotated[PTXServiceChainInfraRequest, fastapi.Body()],
                                              headers: typing.Annotated[PTXServiceChainInfraHeaders, fastapi.Header()],
                                              background: BackgroundTasks,
                                              timeout: typing.Annotated[int, fastapi.Query(gt=0)] = 30,
                                              label: K8sLabelCollectionType = None):
    """Infrastructure service endpoint for creating worker batch asynchronously"""

    async def create_workers_batch_in_background(timeout: int, label: list[str] | None = None):
        logger.debug("Background task is called")
        try:
            worker_status = await create_workers_batch(request=request,
                                                       pews=body.data,
                                                       parallel=True,
                                                       wait=True,
                                                       timeout=timeout,
                                                       label=label)
            pdc_host = CONFIG.PDC_CALLBACK_HOST if CONFIG.PDC_CALLBACK_HOST else request.client.host
            callback_url = f"http://{pdc_host}:3000/service-chain/resume"
            logger.debug(f"Assembled callback url: {callback_url}")
            callback_body = PTXServiceChainResumeCallback.model_validate({
                "chainId": headers.x_ptx_service_chain_id,
                "targetId": headers.x_ptx_target_id,
                "data": worker_status,
                "params": body.params
            })
            logger.debug(f"Assembled callback body:\n{callback_body.model_dump_json(indent=2)}")
            try:
                async with aiohttp.ClientSession() as session:
                    logger.info("Notifying callback...")
                    async with session.post(callback_url,
                                            json=callback_body.model_dump_json(exclude_none=True),
                                            raise_for_status=True) as resp:
                        result = aiohttp.http.HTTPStatus(resp.status)
                        logger.info(f"Received response: HTTP/{result} - {result.name} for callback: {callback_url}")
                        logger.debug(f"Callback response body:\n{await resp.json()}")
            except (aiohttp.ClientError, urllib3.exceptions.MaxRetryError) as ex:
                logger.error(f"Error received during callback invocation on {callback_url}")
                raise_for_network_error(ex)
        except fastapi.HTTPException as ex:
            logger.error(f"Error received in background task: {ex}")
            # Notify service chain about failed task if possible...

    logger.debug("=" * 100)
    logger.info("Received Infrastructure Service async invocation request")
    logger.debug(f"Parsed resource names: {[p.spec.name for p in body.data]}")
    timeout = body.params.get("timeout", timeout) if isinstance(body.params, dict) else timeout
    label = body.params.get("label", label) if isinstance(body.params, dict) else None
    logger.info(f"Schedule background task with execution mode: wait=True, parallel=True, {timeout=}, {label=}")
    background.add_task(create_workers_batch_in_background, timeout=timeout, label=label)
    logger.debug("=" * 100)
    return {"message": "Workers are scheduled for creation!"}


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
