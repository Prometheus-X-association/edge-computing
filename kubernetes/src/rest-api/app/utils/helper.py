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
import collections
import contextlib
import logging
import typing

import anyio
import fastapi
import pydantic_core

from app.model.errors import ClientDisconnectedError
from app.model.ptxedgeworker import PEW
from app.utils.config import CONFIG


def str2bool(s: str | bool | None, *, __true=frozenset(('true', 'yes', 'on', 'y', '1'))) -> bool:
    """Convert a string representing true value to bool"""
    return str(s).lower() in __true


@contextlib.asynccontextmanager
async def cancel_on_disconnect(request: fastapi.Request,
                               logger: logging.Logger = logging.getLogger(__name__),
                               raise_for_disconnect: bool = True):
    """
    Based on: https://jasoncameron.dev/posts/fastapi-cancel-on-disconnect
    """
    async with anyio.create_task_group() as tg:
        async def watch_disconnect():
            while not await request.is_disconnected():
                message = await request.receive()
                if message["type"] == "http.disconnect":
                    # noinspection unresolved-references
                    client = f"{request.client.host}:{request.client.port}" if request.client is not None else "-:-"
                    logger.debug(f'{client} - "{request.method} {request.url.path}" 499 DISCONNECTED')
                    tg.cancel_scope.cancel()
                    logger.warning(f'Request canceled due to disconnected client!')
                    if raise_for_disconnect:
                        raise ClientDisconnectedError
                    break

        # noinspection async-call
        tg.start_soon(watch_disconnect)
        try:
            yield
        finally:
            tg.cancel_scope.cancel()


async def response_collector_wrapper(responses: list[dict[str, typing.Any] | None],
                                     func: typing.Callable[[typing.Any, ...], typing.Awaitable],
                                     *args, **kwarg) -> None:
    responses.append(await func(*args, **kwarg))


def validate_pews_list(pews: list[PEW]) -> list[PEW]:
    if len(pews) < 1:
        raise fastapi.exceptions.RequestValidationError([pydantic_core.ErrorDetails(
            type="missing",
            loc=(0,),
            msg="No worker is defined in the batch!",
            input=pews
        )])
    missing_names = [(i, pew) for i, pew in enumerate(pews) if not pew.spec.name]
    if len(missing_names):
        raise fastapi.exceptions.RequestValidationError([
            pydantic_core.ErrorDetails(
                type="missing",
                loc=(idx, "spec", "name"),
                msg="Worker <spec.name> must be defined for each batch request!",
                input=pew.spec.name
            )
            for idx, pew in missing_names
        ])
    if len(name_occurrences := collections.Counter(pew.spec.name for pew in pews)) < len(pews):
        raise fastapi.exceptions.RequestValidationError([
            pydantic_core.ErrorDetails(
                type="duplicated",
                loc=("spec", "name"),
                msg="Worker <spec.name> must be unique!",
                input=[name for name, count in name_occurrences.items() if count > 1]
            )
        ])
    return pews


########################################################################################################################

def assemble_worker_resource_url(request: fastapi.Request, name: str) -> str:
    if not (proto := next((v for h, v in request.scope['headers'] if h == b'x-forwarded-proto'), b"")):
        proto = request.scope['scheme']
    if not (base := next((v for h, v in request.scope['headers'] if h == b'x-forwarded-host'), b"")):
        base = next((v for h, v in request.scope['headers'] if h == b'host'), b"")
    if not (root_path := request.scope.get('root_path')):
        root_path = CONFIG.ROOT_PATH
    return f"{proto.decode()}://{base.decode()}{root_path}/workers/{name}"


def assemble_worker_endpoint_url(request: fastapi.Request, name: str, secured: bool | None) -> str:
    proto = next((v for h, v in request.scope['headers'] if h == b'x-forwarded-proto'),
                 b"https" if secured else b"http")
    if not (base := next((v for h, v in request.scope['headers'] if h == b'x-forwarded-host'), b"")):
        base = next((v for h, v in request.scope['headers'] if h == b'host'), b"")
    return f"{proto.decode()}://{base.decode()}/worker/{name}"
