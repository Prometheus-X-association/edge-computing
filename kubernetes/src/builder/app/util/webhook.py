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
import http.server
import json
import logging


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
        content_length = int(self.headers.get("Content-Length"))
        try:
            self.server.webhook_data = json.loads(self.rfile.read(content_length))
        except Exception as e:
            self.log_error(str(e))
            self.send_error(http.HTTPStatus.BAD_REQUEST)
            return
        self.send_response(http.HTTPStatus.OK)
        self.end_headers()
        self.server.received = True
        # self.server.shutdown_request(self.request)
        # self.server.shutdown()


class WebHookServer(http.server.HTTPServer):
    DEF_SERVER_ADDR = "0.0.0.0"
    DEF_SERVER_PORT = 8888

    def __init__(self, address=DEF_SERVER_ADDR, port=DEF_SERVER_PORT, timeout=None):
        # noinspection PyTypeChecker
        super().__init__((address, port), HandleWebHook)
        self.timeout = timeout
        self.webhook_data = None
        self.received = False
        self.logger = logging.getLogger(self.__class__.__name__)

    def handle_timeout(self):
        self.logger.error(f"WebHookServer timed out! [{self.timeout}s]")
        raise TimeoutError
        # self.socket.close()

    def wait_for_hook(self):
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
                break
        return self.webhook_data


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    server = WebHookServer('127.0.0.1', 8080, 10)
    data = server.wait_for_hook()
    print(f"{data = }")
