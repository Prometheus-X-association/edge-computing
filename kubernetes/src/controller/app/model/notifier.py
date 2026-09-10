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


class WorkerHandlingState(enum.Flag):
    INDEXED = enum.auto()
    MANAGED = enum.auto()
    CREATED = enum.auto()


class WorkerEventType(enum.StrEnum):
    READY = "ready"
    EXPOSED = "exposed"


@dataclasses.dataclass(init=True, repr=True, frozen=True)
class WorkerStatusNotifier:
    ready: asyncio.Event = dataclasses.field(default_factory=asyncio.Event)
    exposed: asyncio.Event = dataclasses.field(default_factory=asyncio.Event)

    @property
    def events(self):
        return self.ready, self.exposed

    def get(self, _type: WorkerEventType) -> asyncio.Event:
        return getattr(self, _type.value)


class PatchingRequestInterrupt(kopf.TemporaryError):

    def __init__(self):
        super().__init__("Enforce handler reload to allow patching...", 0)
