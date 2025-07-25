#!/usr/bin/env python3
# Copyright 2024 Janos Czentye
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
from __future__ import annotations

import http.client
import http.server
import json
import logging
from concurrent.futures import Executor, Future
from concurrent.futures.thread import ThreadPoolExecutor


class HandleWebHook(http.server.BaseHTTPRequestHandler):
    WEBHOOK_PATH = "/builder/webhook"
    server_version = "PTX-builder/webhook"

    def do_GET(self):
        self.log_error("GET request received.")
        self.send_error(http.HTTPStatus.METHOD_NOT_ALLOWED)

    def do_POST(self):
        if self.path != self.WEBHOOK_PATH:
            self.log_error(f"Not a valid webhook request path: {self.path}")
            self.send_error(http.HTTPStatus.NOT_FOUND)
            return
        if self.headers.get("Content-Type") != "application/json":
            self.log_error(f"Invalid Content-Type: {self.headers.get("Content-Type")}")
            self.send_error(http.HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
            return
        self.server.webhook_headers = self.headers
        content_length = int(self.headers.get("Content-Length"))
        try:
            self.server.webhook_data = json.loads(self.rfile.read(content_length))
        except Exception as e:
            self.log_error(str(e))
            self.send_error(http.HTTPStatus.BAD_REQUEST)
            return
        self.send_response(http.HTTPStatus.OK)
        self.end_headers()
        # no request body
        self.server.received = True


class WebHookServer(http.server.HTTPServer):
    DEF_SERVER_ADDR = "0.0.0.0"
    DEF_SERVER_PORT = 8888

    def __init__(self, address: str = DEF_SERVER_ADDR, port: int = DEF_SERVER_PORT, timeout: int = None):
        # noinspection PyTypeChecker
        super().__init__((address, port), HandleWebHook)
        self.timeout: int | None = timeout
        self.webhook_headers: http.client.HTTPMessage | None = None
        self.webhook_data: dict | None = None
        self.received: bool = False
        self.logger: logging.Logger = logging.getLogger(self.__class__.__name__)

    def handle_timeout(self):
        self.logger.error(f"WebHookServer timed out! [{self.timeout}s]")
        raise TimeoutError
        # self.socket.close()

    def wait_for_hook(self) -> dict:
        self.logger.info("Webhook server listening on http://{0}:{1}{2}...".format(*self.server_address,
                                                                                   HandleWebHook.WEBHOOK_PATH))
        # self.serve_forever()
        while True:
            try:
                self.handle_request()
            except TimeoutError:
                break
            if self.received:
                self.logger.info(f"Webhook for {HandleWebHook.WEBHOOK_PATH} received.")
                self.logger.debug(f"Received request headers:\n{dict(self.webhook_headers)}")
                break
        return self.webhook_data


class WebHooKManager(object):

    def __init__(self, host: str = '0.0.0.0', port: int = 8080, timeout: int = None):
        self.server: WebHookServer = WebHookServer(host, port, timeout)
        self.__executor: Executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix=self.server.__class__.__name__)
        self.__future: Future | None = None

    def start(self):
        self.__future = self.__executor.submit(self.server.wait_for_hook)

    def wait(self) -> dict:
        try:
            return self.__future.result(timeout=self.server.timeout * 2)
        finally:
            self.__executor.shutdown(cancel_futures=True)

    def __enter__(self) -> WebHooKManager:
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__executor.shutdown(wait=False if any((exc_type, exc_val, exc_tb)) else True)


if __name__ == "__main__":
    # curl -X POST -H "Content-Type: application/json" -d '{}' http://127.0.0.1:8080/builder/webhook
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    with WebHooKManager(timeout=30) as mgr:
        print("waiting for webhook...")
        data = mgr.wait()
    print(f"{data = }")
