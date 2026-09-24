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
import enum
import typing

import pydantic
from fastapi import __version__ as fastapi_version
from pydantic import BaseModel, Field

from app import __version__
from app.model.ptxedgeworker import PEW, PEWSpecServiceInterface


class VersionsResponse(BaseModel):
    """API and used framework versions"""
    api: typing.Annotated[str, Field(default=__version__)]
    framework: typing.Annotated[str, Field(default=fastapi_version)]


########################################################################################################################

# noinspection argument-list
PTXEdgeWorkerNameType = typing.Annotated[str, Field(
    description="Worker name",
    pattern=r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?(\\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*$",
    example="worker")
]


class PTXEdgeWorkerResponseState(enum.StrEnum):
    CREATED = enum.auto()
    ERROR = enum.auto()
    MODIFIED = enum.auto()
    DELETED = enum.auto()
    TIMEOUT = enum.auto()


# noinspection argument-list
class PTXEdgeWorkerResponseResource(BaseModel):
    name: PTXEdgeWorkerNameType
    kind: typing.Annotated[str, Field(description="Worker type",
                                      example="PtxEdgeWorker")]
    version: typing.Annotated[str | None, Field(description="Resource version",
                                                example="dataspace.ptx.org/v1alpha1")] = None
    group: typing.Annotated[str | None, Field(description="Resource group", example="dataspace.ptx.org")] = None


class PTXEdgeWorkerEndpoint(BaseModel):
    interface: typing.Annotated[PEWSpecServiceInterface, Field(description="Endpoint interface")]
    exposed: typing.Annotated[bool, Field(description="Interface state", default=False)]
    url: typing.Annotated[pydantic.HttpUrl | None, Field(description="Exposed interface's URL")] = None


class PTXEdgeWorkerResponseApi(BaseModel):
    resource: typing.Annotated[pydantic.HttpUrl | None, Field(description="Worker resource URL")] = None
    endpoints: typing.Annotated[list[PTXEdgeWorkerEndpoint] | None, Field(description="Worker endpoints")] = None


class PTXEdgeWorkerResponse(BaseModel):
    """Created PTXEdgeWorker status"""
    state: typing.Annotated[PTXEdgeWorkerResponseState, Field(description="Worker deployment state")]
    resource: typing.Annotated[PTXEdgeWorkerResponseResource, Field(description="Worker resource", default=None)]
    api: typing.Annotated[PTXEdgeWorkerResponseApi, Field(description="Worker's exposed URLs", default=None)]


########################################################################################################################

class PTXEdgeWorkerCollectionResponseStatus(BaseModel):
    """Worker state"""
    name: typing.Annotated[PTXEdgeWorkerNameType, Field(description="Worker name")]
    state: typing.Annotated[PTXEdgeWorkerResponseState, Field(description="Worker state", default=None)]
    status: typing.Annotated[dict[str, bool] | None, Field(description="Worker status", default=None)]


class PTXEdgeWorkerCollectionResponse(BaseModel):
    workers: typing.Annotated[list[PTXEdgeWorkerCollectionResponseStatus], Field(description="List of worker states")]
    resources: typing.Annotated[list[PEW] | None, Field(description="List of worker resource objects", default=None)]
