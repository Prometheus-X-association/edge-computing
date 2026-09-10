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
import asyncio
import dataclasses
import enum

import kopf


class ResourceState(enum.Flag):
    INDEXED = enum.auto()
    MANAGED = enum.auto()
    CREATED = enum.auto()


@dataclasses.dataclass(init=True, repr=True, frozen=True)
class ResourceNotifier:
    worker: asyncio.Event = dataclasses.field(default_factory=asyncio.Event)


class PatchingRequestInterrupt(kopf.TemporaryError):

    def __init__(self):
        super().__init__("Requesting resource patching", 0)
