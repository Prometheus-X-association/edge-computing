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
import http
import json
import typing

import fastapi
import urllib3
from kubernetes import client

from app.model.responses import PTXEdgeWorkerStatus
from app.utils.logger import logger


def raise_for_k8s_error(obj: dict[str, typing.Any], _status: int) -> None:
    if not http.HTTPStatus(_status).is_success:
        raise fastapi.HTTPException(status_code=_status,
                                    detail={"status": PTXEdgeWorkerStatus.ERROR,
                                            "code": _status,
                                            "resource": {
                                                "name": obj['details']['name'],
                                                "group": obj['details']['group'],
                                                "kind": obj['details']['kind']
                                            }})


def raise_for_failed_k8s_request(ex: client.ApiException) -> None:
    logger.error(convert_k8s_api_error(ex))
    error = json.loads(str(ex.body))
    code = error['code'] if 'code' in error else http.HTTPStatus.UNPROCESSABLE_ENTITY
    raise fastapi.HTTPException(status_code=code,
                                detail={"status": PTXEdgeWorkerStatus.ERROR,
                                        "reason": error['reason'],
                                        "message": error['message'],
                                        "resource": error['details']
                                        })


def raise_for_network_error(ex: urllib3.exceptions.MaxRetryError) -> None:
    logger.error(f"Max retries exceeded: {ex}")
    raise fastapi.HTTPException(status_code=http.HTTPStatus.FAILED_DEPENDENCY,
                                detail={"status": PTXEdgeWorkerStatus.ERROR,
                                        "reason": str(ex.reason),
                                        "message": None,
                                        "resource": {
                                            "url": ex.url
                                        }})


def convert_k8s_api_error(e: client.ApiException) -> str:
    return '\n'.join((f"Error received with status: {e.status} and reason: {e.reason}",
                      "HTTP response body:",
                      json.dumps(json.loads(str(e.body)) if e.body else '{}', indent=2)))
