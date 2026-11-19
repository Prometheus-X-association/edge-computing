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
import pprint
import typing

import aiohttp
import anyio
import fastapi
import urllib3
from kubernetes_asyncio import client

from app.model.errors import (raise_for_k8s_error, raise_for_failed_k8s_request,
                              raise_for_network_error, raise_for_timeout_error)
from app.model.ptxedgeworker import PEW, PEWStatus
from app.model.responses import PTXEdgeWorkerResponseState, PTXEdgeWorkerNameType
from app.utils.config import CONFIG
from app.utils.helper import (cancel_on_disconnect, ClientDisconnectedError, assemble_worker_resource_url,
                              get_k8s_obj_res, response_updater_wrapper, response_collector_wrapper)
from app.utils.k8s import (invoke_k8s_pew_api, K8sAPIMethod, K8sLabelCollectionType, WatcherTimeout,
                           watch_for_pew_resource_state, PTXEdgeWorkerState, assemble_worker_endpoints)
from app.utils.logger import logger, sanitize_model


async def watch_for_worker_status(request: fastapi.Request,
                                  name: PTXEdgeWorkerNameType,
                                  state: PTXEdgeWorkerState,
                                  timeout: int) -> dict[str, typing.Any] | None:
    """Obtain deployed PTX-Edge worker with given name"""
    try:
        _result = None
        async with cancel_on_disconnect(request=request, logger=logger, raise_for_disconnect=True):
            logger.info(f"Watch resource with name: {name} for state: {state}")
            _result = await watch_for_pew_resource_state(name=name,
                                                         state=PTXEdgeWorkerState(state),
                                                         timeout=timeout,
                                                         raise_for_timeout=True)
        logger.debug(f"Obtained status: {state}={_result}")
        if state is PTXEdgeWorkerState.FAILED:
            resp_state = PTXEdgeWorkerResponseState.ERROR
        elif state in (PTXEdgeWorkerState.READY, PTXEdgeWorkerState.EXPOSED):
            resp_state = PTXEdgeWorkerResponseState.RUNNING
        else:
            resp_state = PTXEdgeWorkerResponseState.FINISHED
        response = {
            "name": name,
            "state": resp_state,
            "status": {
                state: _result
            }
        }
        return response
    except* (WatcherTimeout, client.ApiException,
             aiohttp.ClientError, urllib3.exceptions.MaxRetryError,
             ClientDisconnectedError) as exg:
        if len(exg.exceptions) > 1:
            logger.warning(f"Got more than one exception: {exg.exceptions}")
        for ex in exg.exceptions:
            match ex:
                case WatcherTimeout():
                    raise_for_timeout_error(name=name, state=state, timeout=timeout)
                case client.ApiException():
                    raise_for_failed_k8s_request(ex)
                case aiohttp.ClientError() | urllib3.exceptions.MaxRetryError():
                    raise_for_network_error(ex)
                case ClientDisconnectedError():
                    # Add required status code but irrelevant due to client-initiated disconnect event
                    raise fastapi.HTTPException(status_code=fastapi.status.HTTP_204_NO_CONTENT)
                case _:
                    logger.exception(ex)


########################################################################################################################

async def create_pew_worker(request: fastapi.Request,
                            pew: PEW,
                            name: PTXEdgeWorkerNameType | None,
                            labels: K8sLabelCollectionType = None) -> dict[str, typing.Any] | None:
    """Create PTX Edge Computing worker"""
    logger.info(f"Creating worker with name: {name}")
    logger.debug(f"Parsed model:\n{pew.model_dump_json(indent=2, exclude_none=True)}")
    logger.debug("Creating manifest body...")
    manifest: dict[str, typing.Any] = {
        'apiVersion': f"{PEW.group}/{PEW.version}",
        'kind': PEW.kind,
        'metadata': {
            'namespace': CONFIG.WORKER_NS,
            'labels': {
                'ptxedgeworkers.dataspace.ptx.org/tier': 'worker'
            }
        }
    }
    if name:
        manifest['metadata']['name'] = manifest['metadata']['labels']['app.kubernetes.io/name'] = name
    else:
        logger.debug("Setting up auto-generated name for resource!")
        manifest['metadata']['generateName'] = "worker-"
    if labels:
        manifest['metadata']['labels'].update(dict(l.split('=', maxsplit=1) for l in labels if '=' in l))
    if pew.status:
        logger.debug("Remove optional status from resource...")
        pew.status = PEWStatus()
    manifest.update(pew.model_dump(mode="json",
                                   context=dict(expose_secrets=True),
                                   exclude={"status"},
                                   exclude_unset=True,
                                   exclude_none=True))
    try:
        obj, _status = await invoke_k8s_pew_api(method=K8sAPIMethod.CREATE,
                                                body=manifest)
        raise_for_k8s_error(obj=obj, status=_status)
        logger.info(f"Worker created: {get_k8s_obj_res(obj)}")
        logger.debug(f"Obtained resource:\n{sanitize_model(obj, indent=2)}")
        grp, ver = obj['apiVersion'].split('/', maxsplit=1)
        response = {
            "state": PTXEdgeWorkerResponseState.CREATED,
            "resource": {
                "name": obj['metadata']['name'],
                "kind": obj['kind'],
                "group": grp,
                "version": ver,
            },
            "api": {
                "worker": assemble_worker_resource_url(request=request, name=obj['metadata']['name']),
                "endpoints": await assemble_worker_endpoints(request=request, name=obj['metadata']['name'], obj=obj)
            }
        }
        return response
    except client.ApiException as ex:
        raise_for_failed_k8s_request(ex)
    except (aiohttp.ClientError, urllib3.exceptions.MaxRetryError) as ex:
        raise_for_network_error(ex)


async def list_all_incluster_workers(resource: bool,
                                     label: K8sLabelCollectionType = None) -> dict[str, typing.Any] | None:
    """Obtain deployed PTX-Edge worker states and resources filtered by optional labels"""
    try:
        obj, _status = await invoke_k8s_pew_api(method=K8sAPIMethod.LIST,
                                                label_selector=label)
        raise_for_k8s_error(obj=obj, status=_status)
        logger.info(f"Obtained resource: {get_k8s_obj_res(obj)} with size: {len(obj.get("items", []))}")
        logger.debug(f"Obtained response:\n{sanitize_model(obj, indent=2)}")
        response = {"workers": []}
        for w in obj.get("items", []):
            worker = {
                "name": w['metadata']['name'],
                'state': PTXEdgeWorkerResponseState.CREATED
            }
            if w_stat := w.get('status', {}).get('worker', {}):
                if w_stat.get('ready') or w_stat.get('exposed'):
                    worker["state"] = PTXEdgeWorkerResponseState.RUNNING
                elif w_stat.get('succeeded'):
                    worker["state"] = PTXEdgeWorkerResponseState.FINISHED
                elif w_stat.get('failed'):
                    worker["state"] = PTXEdgeWorkerResponseState.ERROR
            response["workers"].append(worker)
        if resource:
            response.update({"resources": obj.get("items", [])})
        return response
    except client.ApiException as ex:
        raise_for_failed_k8s_request(ex)
    except (aiohttp.ClientError, urllib3.exceptions.MaxRetryError) as ex:
        raise_for_network_error(ex)


async def list_all_incluster_worker_endpoints(request: fastapi.Request,
                                              label: K8sLabelCollectionType = None
                                              ) -> list[dict[str, typing.Any]] | None:
    """Obtain deployed PTX-Edge worker states and resources filtered by optional labels"""
    try:
        obj, _status = await invoke_k8s_pew_api(method=K8sAPIMethod.LIST,
                                                label_selector=label)
        raise_for_k8s_error(obj=obj, status=_status)
        logger.info(f"Obtained resource: {get_k8s_obj_res(obj)} with size: {len(obj.get("items", []))}")
        logger.debug(f"Obtained response:\n{sanitize_model(obj, indent=2)}")
        response = []
        for w in obj.get("items", []):
            response.extend(await assemble_worker_endpoints(request=request, name=w['metadata']['name']))
        logger.debug(f"Assembled response body:\n{pprint.pformat(response, sort_dicts=False)}")
        logger.debug("=" * 100)
        return response
    except client.ApiException as ex:
        raise_for_failed_k8s_request(ex)
    except (aiohttp.ClientError, urllib3.exceptions.MaxRetryError) as ex:
        raise_for_network_error(ex)


async def delete_all_incluster_workers(resource: bool = False,
                                       label: K8sLabelCollectionType = None,
                                       tolerance: int = 10,
                                       wait: bool = False) -> dict[str, typing.Any] | None:
    """Delete deployed PTX-Edge workers filtered by optional labels"""
    try:
        obj, _status = await invoke_k8s_pew_api(method=K8sAPIMethod.DELETE_ALL,
                                                label_selector=label,
                                                propagation_policy="Foreground" if wait else "Background",
                                                grace_period_seconds=tolerance)
        raise_for_k8s_error(obj=obj, status=_status)
        logger.info(f"Obtained resource: {get_k8s_obj_res(obj)} with size: {len(obj.get("items", []))}")
        logger.debug(f"Obtained response:\n{pprint.pformat(obj, sort_dicts=False)}")
        response = {
            "workers": [
                {
                    "name": w['metadata']['name'],
                    "state": PTXEdgeWorkerResponseState.DELETED if wait else PTXEdgeWorkerResponseState.TERMINATING
                }
                for w in obj.get("items", [])
            ]
        }
        if resource:
            response.update({"resources": obj.get("items", [])})
        return response
    except client.ApiException as ex:
        raise_for_failed_k8s_request(ex)
    except (aiohttp.ClientError, urllib3.exceptions.MaxRetryError) as ex:
        raise_for_network_error(ex)


async def create_workers_batch(request: fastapi.Request,
                               pews: list[PEW],
                               parallel: bool = False,
                               wait: bool = False,
                               rollback: bool = True,
                               timeout: int = 30,
                               label: K8sLabelCollectionType = None) -> list[dict[str, typing.Any]]:
    """Create batch of named PTX-Edge workers in parallel"""
    responses: list[dict[str, typing.Any]] = []
    try:
        if parallel:
            logger.info("Initiate worker batch creation in <parallel> mode")
            async with anyio.create_task_group() as task_group:
                for pew in pews:
                    # noinspection async-call
                    task_group.start_soon(
                        functools.partial(response_collector_wrapper, responses, create_pew_worker),
                        request, pew, pew.spec.name, label,
                        name=pew.spec.name)
            logger.debug(f"Received create responses:\n{pprint.pformat(responses, sort_dicts=False)}")
            if wait and timeout:
                async with anyio.create_task_group() as task_group:
                    for response in filter(bool, responses):
                        # noinspection async-call
                        task_group.start_soon(
                            functools.partial(response_updater_wrapper, response, watch_for_worker_status),
                            request, response['resource']['name'], PTXEdgeWorkerState.READY, timeout,
                            name=response['resource']['name'])
        else:
            logger.info("Initiate worker batch creation in <serial> mode")
            for pew in pews:
                response = await create_pew_worker(request=request, pew=pew, name=pew.spec.name, labels=label)
                if response:
                    if wait and timeout:
                        status = await watch_for_worker_status(request=request,
                                                               name=response['resource']['name'],
                                                               state=PTXEdgeWorkerState.READY,
                                                               timeout=timeout)
                        response['state'] = status['state'] if status else PTXEdgeWorkerState.FAILED
                    responses.append(response)
        return responses
    except* fastapi.HTTPException as exgroup:
        logger.error(f"Errors received during batch creation: {[e.__class__.__name__ for e in exgroup.exceptions]}!")
        logger.debug(f"Deployment status:\n{pprint.pformat(responses, sort_dicts=False)}")
        details = []
        if rollback:
            logger.info("Reverting worker batch request...")
            for response in filter(bool, responses):
                if response['state'] is not PTXEdgeWorkerResponseState.ERROR:
                    try:
                        logger.debug(f"Deleting resource: {response['resource']['name']}")
                        obj, _status = await invoke_k8s_pew_api(
                            method=K8sAPIMethod.DELETE,
                            name=response['resource']['name'],
                            body=client.V1DeleteOptions(propagation_policy="Foreground" if wait else "Background",
                                                        grace_period_seconds=timeout).to_dict()
                        )
                        raise_for_k8s_error(obj=obj, status=_status)
                        logger.info(f"Deleted resource: {get_k8s_obj_res(obj)}")
                        _state = PTXEdgeWorkerResponseState.DELETED if wait else PTXEdgeWorkerResponseState.TERMINATING
                        details.append({
                            "state": _state,
                            "error_code": fastapi.status.HTTP_200_OK,
                            "resource": response['resource']
                        })
                    except (client.ApiException, aiohttp.ClientError, urllib3.exceptions.MaxRetryError):
                        logger.error(f"Failed to delete resource: {response['resource']['name']}")
                        details.append({
                            "state": PTXEdgeWorkerResponseState.ERROR,
                            "error_code": fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
                            "resource": response['resource']
                        })
                else:
                    details.append(response.copy())
        if len(exgroup.exceptions) > 1:
            logger.warning("Multiple exceptions occurred while creating worker batch!")
        logger.debug("Adding failed worker status to responses...")
        for ex in exgroup.exceptions:
            details.append(getattr(ex, 'detail', {}))
        logger.debug(f"Assembled response body:\n{pprint.pformat(details, sort_dicts=False)}")
        status_code = max((ex.status_code for ex in exgroup.exceptions if hasattr(ex, 'status_code')),
                          default=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR)
        logger.debug(f"Calculated response status code: {status_code}")
        logger.debug("=" * 100)
        raise fastapi.HTTPException(status_code=status_code, detail=details)
