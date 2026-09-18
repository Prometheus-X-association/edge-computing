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
import contextlib
import logging

import anyio
import fastapi

from app.model.errors import ClientDisconnectedError
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
                    client = f"{request.client.host}:{request.client.port}" if request.client else "-:-"
                    logger.debug(f'{client} - "{request.method} {request.url.path}" 499 DISCONNECTED')
                    tg.cancel_scope.cancel()
                    logger.warning(f'Request canceled due to disconnected client!')
                    if raise_for_disconnect:
                        raise ClientDisconnectedError
                    break

        tg.start_soon(watch_disconnect)
        try:
            yield
        finally:
            tg.cancel_scope.cancel()


def assemble_worker_resource_url(request: fastapi.Request, name: str) -> str:
    if not (proto := next((v for h, v in request.scope['headers'] if h == b'x-forwarded-proto'), b"")):
        proto = request.scope['scheme']
    if not (base := next((v for h, v in request.scope['headers'] if h == b'x-forwarded-host'), b"")):
        base = next((v for h, v in request.scope['headers'] if h == b'host'), b"")
    if not (root_path := request.scope.get('root_path')):
        root_path = CONFIG.ROOT_PATH
    return f"{proto.decode()}://{base.decode()}{root_path}/workers/{name}"
