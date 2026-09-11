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
import typing

import kopf


class WorkerHandlingState(enum.Flag):
    INDEXED = enum.auto()
    MANAGED = enum.auto()
    CREATED = enum.auto()


@dataclasses.dataclass(init=True, repr=True, frozen=True)
class WorkerNotifier:
    class EventType(enum.StrEnum):
        READINESS = enum.auto()
        EXPOSED = enum.auto()
        SUCCEEDED = enum.auto()
        FAILED = enum.auto()
        RESULTED = enum.auto()

    readiness: asyncio.Event = dataclasses.field(default_factory=asyncio.Event)
    exposed: asyncio.Event = dataclasses.field(default_factory=asyncio.Event)
    succeeded: asyncio.Event = dataclasses.field(default_factory=asyncio.Event)
    failed: asyncio.Event = dataclasses.field(default_factory=asyncio.Event)
    #
    resulted: asyncio.Queue = dataclasses.field(default_factory=asyncio.Queue)

    def get(self, _type: EventType) -> asyncio.Event | asyncio.Queue:
        return getattr(self, _type.value)

    def generate_tasks(self) -> typing.Generator[asyncio.Task]:
        return (
            asyncio.create_task(
                getattr(self, f.name).wait() if f.type is asyncio.Event else getattr(self, f.name).get(),
                name=self.EventType(f.name))
            for f in dataclasses.fields(self)
        )


class PatchingRequestInterrupt(kopf.TemporaryError):

    def __init__(self):
        super().__init__("Enforce handler reload to allow patching...", 0)
