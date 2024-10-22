import http
import random
import uuid

import connexion
from flask import make_response

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
        return http.HTTPStatus.BAD_REQUEST

    if "restricted" in req.data_contract or "restricted" in req.func_contract:
        return make_response("Request prohibited by contract/consent",
                             http.HTTPStatus.FORBIDDEN)
    elif req.data in (None, "") or req.function in (None, ""):
        return make_response("Execution request parameters not found",
                             http.HTTPStatus.NOT_FOUND)
    elif req.metadata.get("timeout", 100) < 42:
        return make_response("Function deployment timeout",
                             http.HTTPStatus.REQUEST_TIMEOUT)
    elif req.metadata.get("privacy-zone", "zone-A") not in ("zone-A", "zone-C"):
        return make_response("Undeployable request due to privacy zone restriction",
                             http.HTTPStatus.PRECONDITION_FAILED)
    elif req.metadata.get("CPU-demand", 42) > 42:
        return make_response("Insufficient compute resources or unavailable deployment service",
                             http.HTTPStatus.SERVICE_UNAVAILABLE)
    elif any(getattr(req, a) in (None, "") for a in req.swagger_types):
        return make_response("Malformed deployment request", http.HTTPStatus.BAD_REQUEST)

    resp = ExecutionResult(uuid=str(uuid.uuid4()), function=req.function, data=req.data,
                           metrics=ExecutionMetrics(ret=0, elapsed_time=random.randint(0, 10)))
    return make_response(resp.to_dict(), http.HTTPStatus.OK)


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
        return http.HTTPStatus.BAD_REQUEST

    if req.consent in (None, "") or req.token in (None, ""):
        return make_response("Unauthorized request due to invalid token",
                             http.HTTPStatus.UNAUTHORIZED)
    elif "restricted" in req.data_contract or "restricted" in req.func_contract or "restricted" in req.consent:
        return make_response("Request prohibited by contract/consent",
                             http.HTTPStatus.FORBIDDEN)
    elif req.private_data in (None, "") or req.function in (None, ""):
        return make_response("Execution request parameters not found",
                             http.HTTPStatus.NOT_FOUND)
    elif req.metadata.get("timeout", 100) < 42:
        return make_response("Function deployment timeout",
                             http.HTTPStatus.REQUEST_TIMEOUT)
    elif req.metadata.get("privacy-zone", "zone-A") not in ("zone-A", "zone-C"):
        return make_response("Undeployable request due to privacy zone restriction",
                             http.HTTPStatus.PRECONDITION_FAILED)
    elif req.metadata.get("CPU-demand", 42) > 42:
        return make_response("Insufficient compute resources or unavailable deployment service",
                             http.HTTPStatus.SERVICE_UNAVAILABLE)
    elif any(getattr(req, a) in (None, "") for a in req.swagger_types):
        return make_response("Malformed deployment request",
                             http.HTTPStatus.BAD_REQUEST)

    if any(getattr(req, a) in (None, "") for a in req.swagger_types):
        return make_response("Unsupported format", http.HTTPStatus.BAD_REQUEST)
    resp_body = PrivateExecutionResult(uuid=str(uuid.uuid4()), function=req.function, private_data=req.private_data,
                                       metrics=ExecutionMetrics(ret=0, elapsed_time=random.randint(0, 10)))
    return make_response(resp_body.to_dict(), http.HTTPStatus.OK)
