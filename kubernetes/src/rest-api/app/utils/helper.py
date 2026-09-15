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


def str2bool(s: str | bool | None, *, __true=frozenset(('true', 'yes', 'on', 'y', '1'))) -> bool:
    return str(s).lower() in __true


@contextlib.asynccontextmanager
async def cancel_on_disconnect(request: fastapi.Request, logger: logging.Logger = logging.getLogger(__name__)):
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
                    logger.warning(f'Request canceled due to client disconnect!')
                    break

        tg.start_soon(watch_disconnect)
        try:
            yield
        finally:
            tg.cancel_scope.cancel()
