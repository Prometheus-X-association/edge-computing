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

# generated by fastapi-codegen:
#   filename:  openapi_design.json
#   timestamp: 2025-05-20T13:46:51+00:00
from __future__ import annotations

import json
import random
import uuid

from fastapi import FastAPI, status, Request, __version__ as fastapi_version
from fastapi.exceptions import RequestValidationError, HTTPException
from fastapi.responses import JSONResponse

from . import ROUTE_PREFIX, __version__
from .models import *

app = FastAPI(contact={'email': 'czentye.janos@vik.bme.hu'},
              description='The Edge Computing (Decentralized AI processing) BB-02 provides value-added services '
                          'exploiting an underlying distributed edge computing infrastructure.',
              title='PTX Edge Computing REST-API',
              version=__version__,
              root_path=ROUTE_PREFIX,
              servers=[dict(url=ROUTE_PREFIX,
                            description="PTX Edge Computing")],
              docs_url="/ui/",
              redoc_url="/ui/")


@app.get('/versions', status_code=status.HTTP_200_OK)
async def get_versions_versions_get() -> VersionResponse:
    """Versions of the REST-API component"""
    return VersionResponse(api=__version__, framework=fastapi_version)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(req: Request, exc: RequestValidationError):
    try:
        body = await req.json()
    except json.decoder.JSONDecodeError:
        return JSONResponse(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                            content={'detail': "Unsupported request format"})

    if str(req.url).endswith("requestEdgeProc"):
        if any(body.get(p) is None for p in ('data', 'data_contract', 'func_contract', 'function')):
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                                content={'detail': "Execution request parameters not found"})
    elif str(req.url).endswith("requestPrivacyEdgeProc"):
        if any(body.get(p) in (None, "") for p in ('consent', 'token')):
            return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED,
                                content={'detail': "Unauthorized request due to invalid token"})
        elif any(body.get(p) in (None, "") for p in
                 ('private_data', 'data_contract', 'func_contract', 'function', 'token')):
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                                content={'detail': "Execution request parameters not found"})
    return JSONResponse(str(exc), status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


########################################################################################################################

ERROR_RESPONSES = {
    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE:
        {"content": None, "description": "Unsupported request format"},
    status.HTTP_401_UNAUTHORIZED:
        {"content": None, "description": "Unauthorized request due to invalid token"},
    status.HTTP_404_NOT_FOUND:
        {"content": None, "description": "Execution request parameters not found"},
    status.HTTP_400_BAD_REQUEST:
        {"content": None, "description": "Malformed deployment request"},
    status.HTTP_403_FORBIDDEN:
        {"content": None, "description": "Request prohibited by contract/consent"},
    status.HTTP_408_REQUEST_TIMEOUT:
        {"content": None, "description": "Function deployment timeout"},
    status.HTTP_412_PRECONDITION_FAILED:
        {"content": None, "description": "Undeployable request due to privacy zone restriction"},
    status.HTTP_503_SERVICE_UNAVAILABLE:
        {"content": None, "description": "Insufficient compute resources or unavailable deployment service"}
}


@app.post('/requestEdgeProc', status_code=status.HTTP_202_ACCEPTED, tags=['customerAPI'],
          responses=ERROR_RESPONSES)
async def request_edge_proc(body: ExecutionRequestBody) -> ExecutionResult:
    """
    Execute function on data
    """
    if any(getattr(body, p) in (None, "") for p in ('data', 'function')):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed deployment request")
    elif any(getattr(body, p) is None for p in ('data', 'data_contract', 'func_contract', 'function')):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution request parameters not found")

    if "bogus" in body.data_contract or "bogus" in body.func_contract:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Request prohibited by contract/consent")
    metadata = body.metadata.model_dump()
    if metadata.get("timeout", 100) < 42:
        raise HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT,
                            detail="Function deployment timeout")
    elif metadata.get("privacy-zone", "zone-A") not in ("zone-A", "zone-C"):
        raise HTTPException(status_code=status.HTTP_412_PRECONDITION_FAILED,
                            detail="Undeployable request due to privacy zone restriction")
    elif metadata.get("CPU-demand", 42) > 42:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Insufficient compute resources or unavailable deployment service")

    return ExecutionResult(uuid=uuid.uuid4(), function=body.function, data=body.data,
                           metrics=ExecutionMetrics(ret=0, elapsedTime=random.randint(0, 10)))


########################################################################################################################

PRIV_ERROR_RESPONSES = {
    status.HTTP_401_UNAUTHORIZED:
        {"content": None, "description": "Unauthorized request due to invalid token"},
    **ERROR_RESPONSES
}


@app.post('/requestPrivacyEdgeProc', status_code=status.HTTP_202_ACCEPTED, tags=['customerAPI'],
          responses=PRIV_ERROR_RESPONSES)
def request_privacy_edge_proc(body: PrivateExecutionRequestBody) -> PrivateExecutionResult:
    """
    Execute function on private data
    """

    if any(getattr(body, p) in (None, "") for p in ('private_data', 'function')):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed deployment request")
    elif any(getattr(body, p) is None for p in ('private_data', 'data_contract', 'func_contract', 'function', 'token')):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution request parameters not found")

    if "bogus" in body.data_contract or "bogus" in body.func_contract or "bogus" in body.consent:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Request prohibited by contract/consent")
    metadata = body.metadata.model_dump()
    if metadata.get("timeout", 100) < 42:
        raise HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT,
                            detail="Function deployment timeout")
    elif metadata.get("privacy-zone", "zone-A") not in ("zone-A", "zone-C"):
        raise HTTPException(status_code=status.HTTP_412_PRECONDITION_FAILED,
                            detail="Undeployable request due to privacy zone restriction")
    elif metadata.get("CPU-demand", 42) > 42:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Insufficient compute resources or unavailable deployment service")

    return PrivateExecutionResult(uuid=uuid.uuid4(), function=body.function, private_data=body.private_data,
                                  metrics=ExecutionMetrics(ret=0, elapsedTime=random.randint(0, 10)))
