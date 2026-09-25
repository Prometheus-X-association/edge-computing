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
import json
import typing

import aiohttp
import fastapi
import urllib3
from kubernetes_asyncio import client
from pydantic import BaseModel, Field

from app.model.ptxedgeworker import PEW
from app.model.responses import PTXEdgeWorkerResponseState
from app.utils.logger import logger


class ClientDisconnectedError(RuntimeError):
    pass


class PTXEdgeAPIErrorDetail(BaseModel):
    state: typing.Annotated[PTXEdgeWorkerResponseState, Field(description="Worker Status")]
    error_code: typing.Annotated[int | None, Field(description="Status code")] = None
    reason: typing.Annotated[str | None, Field(description="Cause of error")] = None
    message: typing.Annotated[str | None, Field(description="Detailed error message")] = None
    resource: typing.Annotated[dict[str, typing.Any] | None, Field(description="Worker resource")] = None


class PTXEdgeAPIError(BaseModel):
    detail: typing.Annotated[PTXEdgeAPIErrorDetail | list[PTXEdgeAPIErrorDetail], Field(description="Error details")]


########################################################################################################################

def raise_for_k8s_error(obj: dict[str, typing.Any], status: int) -> None:
    result = http.HTTPStatus(status)
    name = obj.get('metadata', {}).get('name') if 'metadata' in obj else obj.get('details', {}).get('name')
    logger.debug(f"Received response: HTTP/{result} - {result.name} for {obj.get('kind')}/{name}")
    if not result.is_success:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_502_BAD_GATEWAY,
            detail={
                "state": PTXEdgeWorkerResponseState.ERROR,
                "error_code": status,
                "resource": {
                    "name": obj['details']['name'],
                    "group": obj['details']['group'],
                    "kind": obj['details']['kind']
                }
            })


def raise_for_failed_k8s_request(ex: client.ApiException) -> None:
    error = json.loads(ex.body.decode() if isinstance(ex.body, bytes) else str(ex.body)) if ex.body else {}
    logger.error('\n'.join((f"Error received with status: {ex.status} and reason: {ex.reason}",
                            "Received HTTP body:",
                            json.dumps(error, indent=2))))
    if (code := int(error.get('code', 0))) not in (fastapi.status.HTTP_422_UNPROCESSABLE_CONTENT,
                                                   fastapi.status.HTTP_409_CONFLICT,
                                                   fastapi.status.HTTP_404_NOT_FOUND):
        code = fastapi.status.HTTP_502_BAD_GATEWAY
    raise fastapi.HTTPException(
        status_code=code,
        detail={
            "state": PTXEdgeWorkerResponseState.ERROR,
            "error_code": code,
            "reason": error['reason'],
            "message": error['message'],
            "resource": error['details']
        }) from ex


def raise_for_network_error(ex: urllib3.exceptions.MaxRetryError | aiohttp.ClientError) -> None:
    logger.error(f"Network error received: {ex}")
    raise fastapi.HTTPException(
        status_code=fastapi.status.HTTP_502_BAD_GATEWAY,
        detail={
            "state": PTXEdgeWorkerResponseState.ERROR,
            "error_code": fastapi.status.HTTP_502_BAD_GATEWAY,
            "reason": f"{ex.__class__.__name__}",
            "message": str(ex.reason) if hasattr(ex, 'reason') else str(ex),
            "resource": {}
        }) from ex


def raise_for_timeout_error(name: str, state: str, timeout: int) -> None:
    raise fastapi.HTTPException(
        status_code=fastapi.status.HTTP_502_BAD_GATEWAY,
        detail={
            "state": PTXEdgeWorkerResponseState.TIMEOUT,
            "error_code": fastapi.status.HTTP_408_REQUEST_TIMEOUT,
            "reason": f"RequestTimeout",
            "message": f"Waiting for {state=!s} in worker[{name}] reached timeout: {timeout}s!",
            "resource": {
                "name": name,
                "group": PEW.group,
                "kind": PEW.kind,
            }
        })
