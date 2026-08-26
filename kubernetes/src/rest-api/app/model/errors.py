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
from http import HTTPStatus

import fastapi
import urllib3
from kubernetes import client
from pydantic import BaseModel, Field

from app.model.responses import PTXEdgeWorkerResponseStatus
from app.utils.logger import logger


class PTXEdgeAPIErrorDetail(BaseModel):
    status: typing.Annotated[PTXEdgeWorkerResponseStatus, Field(description="Worker Status")]
    error_code: typing.Annotated[int | None, Field(description="Status code", default=None)]
    reason: typing.Annotated[str | None, Field(description="Cause of error", default=None)]
    message: typing.Annotated[str | None, Field(description="Detailed error message", default=None)]
    resource: typing.Annotated[dict[str, typing.Any] | None, Field(description="Worker resource", default=None)]


class PTXEdgeAPIError(BaseModel):
    detail: typing.Annotated[PTXEdgeAPIErrorDetail, Field(description="Error details")]


def raise_for_k8s_error(obj: dict[str, typing.Any], status: int) -> None:
    result = http.HTTPStatus(status)
    logger.debug(f"Received response: HTTP/{result} - {result.name}")
    if not result.is_success:
        raise fastapi.HTTPException(status_code=HTTPStatus.FAILED_DEPENDENCY,
                                    detail={"status": PTXEdgeWorkerResponseStatus.ERROR,
                                            "error_code": status,
                                            "resource": {
                                                "name": obj['details']['name'],
                                                "group": obj['details']['group'],
                                                "kind": obj['details']['kind']
                                            }})


def raise_for_failed_k8s_request(ex: client.ApiException) -> None:
    logger.error(convert_k8s_api_error(ex))
    error = json.loads(str(ex.body))
    code = error.get('code')
    match code:
        case 422:
            code = HTTPStatus.NOT_ACCEPTABLE
        case 409:
            code = HTTPStatus.CONFLICT
        case _:
            code = HTTPStatus.FAILED_DEPENDENCY
    raise fastapi.HTTPException(status_code=code,
                                detail={"status": PTXEdgeWorkerResponseStatus.ERROR,
                                        "error_code": error.get('code'),
                                        "reason": error['reason'],
                                        "message": error['message'],
                                        "resource": error['details']
                                        })


def raise_for_network_error(ex: urllib3.exceptions.MaxRetryError) -> None:
    logger.error(f"Max retries exceeded: {ex}")
    raise fastapi.HTTPException(status_code=http.HTTPStatus.FAILED_DEPENDENCY,
                                detail={"status": PTXEdgeWorkerResponseStatus.ERROR,
                                        "reason": f"{ex.__class__.__name__}",
                                        "message": str(ex.reason),
                                        "resource": {
                                            "url": ex.url
                                        }})


def convert_k8s_api_error(e: client.ApiException) -> str:
    return '\n'.join((f"Error received with status: {e.status} and reason: {e.reason}",
                      "HTTP response body:",
                      json.dumps(json.loads(str(e.body)) if e.body else '{}', indent=2)))
