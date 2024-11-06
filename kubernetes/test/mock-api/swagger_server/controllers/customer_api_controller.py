# Copyright 2024 Janos Czentye
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
import random
import uuid

import connexion
from flask import make_response, abort

from swagger_server.models.execution_metrics import ExecutionMetrics
from swagger_server.models.execution_request_body import ExecutionRequestBody  # noqa: E501
from swagger_server.models.execution_result import ExecutionResult  # noqa: E501
from swagger_server.models.private_execution_request_body import PrivateExecutionRequestBody  # noqa: E501
from swagger_server.models.private_execution_result import PrivateExecutionResult  # noqa: E501


def request_edge_proc(body):  # noqa: E501
    """Execute function on data

     # noqa: E501

    :param body: 
    :type body: dict | bytes

    :rtype: ExecutionResult
    """
    if connexion.request.is_json:
        req = ExecutionRequestBody.from_dict(connexion.request.get_json())  # noqa: E501
    else:
        return abort(http.HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "Unsupported request format")

    if "restricted" in req.data_contract or "restricted" in req.func_contract:
        return abort(http.HTTPStatus.FORBIDDEN,
                     "Request prohibited by contract/consent")
    elif req.data in (None, "") or req.function in (None, ""):
        return abort(http.HTTPStatus.NOT_FOUND,
                     "Execution request parameters not found")
    elif req.metadata.get("timeout", 100) < 42:
        return abort(http.HTTPStatus.REQUEST_TIMEOUT,
                     "Function deployment timeout")
    elif req.metadata.get("privacy-zone", "zone-A") not in ("zone-A", "zone-C"):
        return abort(http.HTTPStatus.PRECONDITION_FAILED,
                     "Undeployable request due to privacy zone restriction")
    elif req.metadata.get("CPU-demand", 42) > 42:
        return abort(http.HTTPStatus.SERVICE_UNAVAILABLE,
                     "Insufficient compute resources or unavailable deployment service")
    elif any(getattr(req, a) in (None, "") for a in req.swagger_types):
        return abort(http.HTTPStatus.BAD_REQUEST, "Malformed deployment request")

    resp = ExecutionResult(uuid=str(uuid.uuid4()), function=req.function, data=req.data,
                           metrics=ExecutionMetrics(ret=0, elapsed_time=random.randint(0, 10)))
    return make_response(resp.to_dict(), http.HTTPStatus.ACCEPTED)


def request_privacy_edge_proc(body):  # noqa: E501
    """Execute function on private data

     # noqa: E501

    :param body: 
    :type body: dict | bytes

    :rtype: PrivateExecutionResult
    """
    if connexion.request.is_json:
        req = PrivateExecutionRequestBody.from_dict(connexion.request.get_json())  # noqa: E501
    else:
        return abort(http.HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "Unsupported request format")

    if req.consent in (None, "") or req.token in (None, ""):
        return abort(http.HTTPStatus.UNAUTHORIZED,
                     "Unauthorized request due to invalid token")
    elif "restricted" in req.data_contract or "restricted" in req.func_contract or "restricted" in req.consent:
        return abort(http.HTTPStatus.FORBIDDEN,
                     "Request prohibited by contract/consent")
    elif req.private_data in (None, "") or req.function in (None, ""):
        return abort(http.HTTPStatus.NOT_FOUND,
                     "Execution request parameters not found")
    elif req.metadata.get("timeout", 100) < 42:
        return abort(http.HTTPStatus.REQUEST_TIMEOUT,
                     "Function deployment timeout")
    elif req.metadata.get("privacy-zone", "zone-A") not in ("zone-A", "zone-C"):
        return abort(http.HTTPStatus.PRECONDITION_FAILED,
                     "Undeployable request due to privacy zone restriction")
    elif req.metadata.get("CPU-demand", 42) > 42:
        return abort(http.HTTPStatus.SERVICE_UNAVAILABLE,
                     "Insufficient compute resources or unavailable deployment service")
    elif any(getattr(req, a) in (None, "") for a in req.swagger_types):
        return abort(http.HTTPStatus.BAD_REQUEST,
                     "Malformed deployment request")

    if any(getattr(req, a) in (None, "") for a in req.swagger_types):
        return abort(http.HTTPStatus.BAD_REQUEST, "Unsupported format")
    resp_body = PrivateExecutionResult(uuid=str(uuid.uuid4()), function=req.function, private_data=req.private_data,
                                       metrics=ExecutionMetrics(ret=0, elapsed_time=random.randint(0, 10)))
    return make_response(resp_body.to_dict(), http.HTTPStatus.ACCEPTED)
