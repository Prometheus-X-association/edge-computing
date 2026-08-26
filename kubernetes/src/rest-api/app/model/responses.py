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

import fastapi
from pydantic import BaseModel, Field

from app import __version__
from app.model.ptxedgeworker import PEW


class VersionsResponse(BaseModel):
    """API and used framework versions"""
    api: typing.Annotated[str, Field(default=__version__)]
    framework: typing.Annotated[str, Field(default=fastapi.__version__)]


class PTXEdgeWorkerResponseStatus(enum.StrEnum):
    INITIALIZED = enum.auto()
    ERROR = enum.auto()
    TERMINATING = enum.auto()


PTXEdgeWorkerNameType = typing.Annotated[str, Field(description="Worker name",
                                                    pattern=r"^[a-zA-Z0-9_-]+$",
                                                    example="worker")]


class PTXEdgeWorkerResponseResource(BaseModel):
    name: PTXEdgeWorkerNameType
    kind: typing.Annotated[str, Field(description="Resource type",
                                      min_length=1,
                                      example="PtxEdgeWorker")]
    version: typing.Annotated[str | None, Field(description="Resource version",
                                                example="dataspace.ptx.org/v1alpha1")] = None
    group: typing.Annotated[str | None, Field(description="Resource group",
                                              example="dataspace.ptx.org")] = None


class PTXEdgeWorkerResponse(BaseModel):
    """Created PTXEdgeWorker status"""
    status: typing.Annotated[PTXEdgeWorkerResponseStatus, Field(description="Worker deployment status")]
    resource: typing.Annotated[PTXEdgeWorkerResponseResource, Field(description="Worker resource", default=None)]


class PTXEdgeWorkerState(BaseModel):
    """Worker state"""
    name: typing.Annotated[PTXEdgeWorkerNameType, Field(description="Worker name")]
    state: typing.Annotated[str | None, Field(description="Worker state", default=None)]


class PTXEdgeWorkerCollectionResponse(BaseModel):
    workers: typing.Annotated[list[PTXEdgeWorkerState], Field(description="List of worker states")]
    resources: typing.Annotated[list[PEW] | None, Field(description="List of PtxEdgeWorkers", default=None)]
