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
import argparse
import base64
import http
import json
import os
import pathlib
import sys
import tempfile
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, HTTPServer


class AuthenticatedHandler(SimpleHTTPRequestHandler):

    def send_missing_auth(self):
        self.log_error("Incorrect username or password")
        self.send_response(http.HTTPStatus.UNAUTHORIZED)
        self.send_header("WWW-Authenticate", "Basic realm=\"Test\"")
        self.send_header("Content-type", "application/json")
        self.end_headers()

    def do_GET(self):
        auth_header = self.headers.get('Authorization')
        if auth_header == f'Basic {self.server.credential}':
            super().do_GET()
        else:
            self.send_missing_auth()
            print("Received authorization header:", auth_header)
            resp = {'success': False,
                    'error': 'No authorization header' if auth_header is None else 'Invalid credentials'}
            self.wfile.write(json.dumps(resp).encode('utf-8'))


class AuthenticatedHTTPServer(HTTPServer):

    def __init__(self, host: str, port: str, directory):
        self.directory = directory
        self.__key = None
        # noinspection PyTypeChecker
        super().__init__((host, port), AuthenticatedHandler)

    @property
    def credential(self):
        return self.__key

    @credential.setter
    def credential(self, user_pass: tuple[str, str]):
        self.__key = base64.b64encode("{}:{}".format(*user_pass).encode('utf-8')).decode('ascii')

    def finish_request(self, request, client_address):
        self.RequestHandlerClass(request, client_address, self, directory=self.directory)


def run(args):
    with AuthenticatedHTTPServer(args.bind, args.port, args.directory) as httpd:
        if args.auth:
            try:
                creds = args.auth.split(':', maxsplit=1)
                httpd.credential = (creds[0], creds[1])
            except ValueError:
                print("Invalid auth credentials [username:password]!")
                sys.exit(1)
        print("Serving HTTP on {0} port {1} (http://{0}:{1}/)...".format(*httpd.server_address))
        try:
            print(" - Configured credential key:", httpd.credential)
            print(" - Served directory:", httpd.directory)
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nKeyboard interrupt received, exiting.")
            sys.exit(0)


if __name__ == '__main__':
    # ./basic_auth_server.py -b 127.0.0.1 -p 9000 -a demo:demo -m datetime.txt
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--auth', metavar='AUTH', default="demo:demo",
                        help='HTTP basic authentication credentials [default: %(default)s]')
    parser.add_argument('-b', '--bind', metavar='ADDRESS', default='127.0.0.1',
                        help='bind to this address (default: %(default)s)')
    parser.add_argument('-d', '--directory', default=os.getcwd(),
                        help='serve this directory (default: current directory)')
    parser.add_argument('-m', '--mock',
                        help='mock server with given filename in an empty temporary dir')
    parser.add_argument('-p', '--port', default=9000, type=int,
                        help='bind to this port (default: %(default)s)')
    args = parser.parse_args()
    if args.mock:
        with tempfile.TemporaryDirectory(dir="/tmp", delete=True) as tmpdir:
            pathlib.Path(tmpdir, args.mock).write_text(datetime.now().isoformat())
            args.directory = tmpdir
            run(args)
    else:
        run(args)
