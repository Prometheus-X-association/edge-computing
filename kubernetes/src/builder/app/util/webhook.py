#!/usr/bin/env python3
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
import email
import http.client
import http.server
import json
import logging
import sys
import typing
from concurrent.futures import Executor, Future
from concurrent.futures.thread import ThreadPoolExecutor


class WebHookServer(http.server.HTTPServer):
    DEF_SERVER_ADDR = "0.0.0.0"
    DEF_SERVER_PORT = 9999
    REQUEST_WAIT_STEP = 1

    def __init__(self, address: str = DEF_SERVER_ADDR, port: int = DEF_SERVER_PORT, wait_time: int | None = None):
        # noinspection PyTypeChecker
        super().__init__((address, port), HandleWebHook)
        self.timeout: int = self.REQUEST_WAIT_STEP
        self.__wait_ttl: int | None = wait_time // self.REQUEST_WAIT_STEP if wait_time else None
        self.__aborted: bool = False
        self.webhook_headers: email.message.Message | None = None
        self.__webhook_data: dict | None = None
        self.__received: bool = False
        self.logger: logging.Logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug("Webhook server initialized.")

    def set_data(self, webhook_data: dict):
        self.__webhook_data = webhook_data
        self.__received = True
        self.logger.debug("Webhook data received.")

    def wait_for_hook(self) -> dict | None:
        self.logger.info("Webhook server listening on http://{0}:{1}{2}...".format(*self.server_address,
                                                                                   HandleWebHook.WEBHOOK_PATH))
        # self.serve_forever()
        while True:
            try:
                self.handle_request()
            except TimeoutError:
                self.logger.warning(f"{self.__class__.__name__} timed out!")
                break
            else:
                if self.__aborted:
                    self.logger.warning(f"{self.__class__.__name__} aborted!")
                    break
                if self.__received:
                    self.logger.info(f"Webhook for {HandleWebHook.WEBHOOK_PATH} received.")
                    self.logger.debug(f"Received request headers:\n"
                                      f"{dict(self.webhook_headers.items()) if self.webhook_headers else None}")
                    break
        return self.__webhook_data

    def handle_timeout(self) -> None:
        if self.__wait_ttl is not None:
            if self.__wait_ttl <= 0:
                raise TimeoutError
            else:
                self.__wait_ttl -= 1

    def abort(self):
        self.logger.warning("Aborting webhook server...")
        self.__aborted = True


class HandleWebHook(http.server.BaseHTTPRequestHandler):
    WEBHOOK_PATH = "/webhook"
    server_version = f"{WebHookServer.__name__}/webhook"
    server: WebHookServer

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
        content_length = int(self.headers.get("Content-Length", 0))
        try:
            json_body = json.loads(self.rfile.read(content_length))
        except Exception as e:
            self.log_error(str(e))
            self.send_error(http.HTTPStatus.BAD_REQUEST)
            return
        self.send_response(http.HTTPStatus.OK)
        self.end_headers()
        # no response body
        self.server.set_data(json_body)


class WebHooKManager(object):

    def __init__(self, host: str = '0.0.0.0', port: int = 9999, timeout: int | None = None):
        self.server: WebHookServer = WebHookServer(host, port, timeout)
        self.__timeout = timeout
        self.__executor: Executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix=self.server.__class__.__name__)
        self.__future: Future | None = None

    def start(self):
        if self.__future:
            raise RuntimeError("WebHooKManager already started!")
        self.__future = self.__executor.submit(self.server.wait_for_hook)

    def wait(self) -> dict | None:
        if not self.__future:
            raise RuntimeError(f"{self.__class__.__name__} has not yet started!")
        try:
            return self.__future.result(timeout=self.__timeout * 2 if self.__timeout else None)
        except TimeoutError:
            pass
        finally:
            self.__executor.shutdown(wait=True, cancel_futures=True)

    def __enter__(self) -> typing.Self:
        self.start()
        return self

    def __exit__(self, *args):
        if any(args):
            self.server.abort()
        self.__executor.shutdown(wait=True, cancel_futures=True)


def test_webhook(timeout: int | None = None):
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    with WebHooKManager(timeout=timeout if timeout else None) as mgr:
        logging.info(f"Waiting for webhook[{timeout=}]...")
        data = mgr.wait()
        logging.info("Webhook wait finished.")
    print(f"Received {data = }")


if __name__ == "__main__":
    # For example:
    # python3 webhook.py
    # python3 webhook.py 10
    #
    # curl -X POST -H "Content-Type: application/json" -d '{"xyz": 42}' http://127.0.0.1:9999/webhook
    test_webhook(timeout=int(sys.argv[1]) if len(sys.argv) > 1 else None)
