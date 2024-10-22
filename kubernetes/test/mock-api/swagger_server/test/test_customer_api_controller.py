# coding: utf-8
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

from __future__ import absolute_import

import pathlib

from flask import json

from swagger_server.models import ExecutionResult, PrivateExecutionResult
from swagger_server.models.execution_request_body import ExecutionRequestBody  # noqa: E501
from swagger_server.models.private_execution_request_body import PrivateExecutionRequestBody  # noqa: E501
from swagger_server.test import BaseTestCase


class TestCustomerAPIController(BaseTestCase):
    """CustomerAPIController integration test stubs"""

    def test_request_edge_proc_ok(self):
        """Test case for valid request_edge_proc request: HTTP 200

        Execute function on data
        """
        with open(pathlib.Path(__file__).parent / "data/edge_proc_req_def.json") as req:
            body = ExecutionRequestBody.from_dict(json.load(req))
        response = self.client.open(
            '/requestEdgeProc',
            method='POST',
            data=json.dumps(body),
            content_type='application/json')
        resp_body = ExecutionResult.from_dict(json.loads(response.data.decode('utf-8')))
        self.assert200(response,
                       'Response body is : ' + resp_body.to_str())

    def test_request_edge_proc_fail400(self):
        """Test case for invalid request_edge_proc request: HTTP 400

        Execute function on data
        """
        with open(pathlib.Path(__file__).parent / "data/edge_proc_req_def.json") as req:
            body = ExecutionRequestBody.from_dict(json.load(req))
        body.metadata = ""
        response = self.client.open(
            '/requestEdgeProc',
            method='POST',
            data=json.dumps(body),
            content_type='application/json')
        self.assertStatus(response, 400,
                          'Response body is : ' + response.data.decode('utf-8'))

    def test_request_edge_proc_fail403(self):
        """Test case for invalid request_edge_proc request: HTTP 403

        Execute function on data
        """
        with open(pathlib.Path(__file__).parent / "data/edge_proc_req_def.json") as req:
            body = ExecutionRequestBody.from_dict(json.load(req))
        body.func_contract += "-restricted"
        response = self.client.open(
            '/requestEdgeProc',
            method='POST',
            data=json.dumps(body),
            content_type='application/json')
        self.assertStatus(response, 403,
                          'Response body is : ' + response.data.decode('utf-8'))

    def test_request_edge_proc_fail404(self):
        """Test case for invalid request_edge_proc request: HTTP 404

        Execute function on data
        """
        with open(pathlib.Path(__file__).parent / "data/edge_proc_req_def.json") as req:
            body = ExecutionRequestBody.from_dict(json.load(req))
        body.function = ""
        response = self.client.open(
            '/requestEdgeProc',
            method='POST',
            data=json.dumps(body),
            content_type='application/json')
        self.assertStatus(response, 404,
                          'Response body is : ' + response.data.decode('utf-8'))

    def test_request_edge_proc_fail408(self):
        """Test case for invalid request_edge_proc request: HTTP 408

        Execute function on data
        """
        with open(pathlib.Path(__file__).parent / "data/edge_proc_req_def.json") as req:
            body = ExecutionRequestBody.from_dict(json.load(req))
        body.metadata['timeout'] = 0
        response = self.client.open(
            '/requestEdgeProc',
            method='POST',
            data=json.dumps(body),
            content_type='application/json')
        self.assertStatus(response, 408,
                          'Response body is : ' + response.data.decode('utf-8'))

    def test_request_edge_proc_fail412(self):
        """Test case for invalid request_edge_proc request: HTTP 412

        Execute function on data
        """
        with open(pathlib.Path(__file__).parent / "data/edge_proc_req_def.json") as req:
            body = ExecutionRequestBody.from_dict(json.load(req))
        body.metadata['privacy-zone'] = "zone-B"
        response = self.client.open(
            '/requestEdgeProc',
            method='POST',
            data=json.dumps(body),
            content_type='application/json')
        self.assertStatus(response, 412,
                          'Response body is : ' + response.data.decode('utf-8'))

    def test_request_edge_proc_fail503(self):
        """Test case for invalid request_edge_proc request: HTTP 503

        Execute function on data
        """
        with open(pathlib.Path(__file__).parent / "data/edge_proc_req_def.json") as req:
            body = ExecutionRequestBody.from_dict(json.load(req))
        body.metadata['CPU-demand'] = 100
        response = self.client.open(
            '/requestEdgeProc',
            method='POST',
            data=json.dumps(body),
            content_type='application/json')
        self.assertStatus(response, 503,
                          'Response body is : ' + response.data.decode('utf-8'))

    def test_request_privacy_edge_proc_ok(self):
        """Test case for valid request_privacy_edge_proc request: HTTP 200

        Execute function on private data
        """
        with open(pathlib.Path(__file__).parent / "data/priv_edge_proc_req_def.json") as req:
            body = PrivateExecutionRequestBody.from_dict(json.load(req))
        response = self.client.open(
            '/requestPrivacyEdgeProc',
            method='POST',
            data=json.dumps(body),
            content_type='application/json')
        resp_body = PrivateExecutionResult.from_dict(json.loads(response.data.decode('utf-8')))
        self.assert200(response,
                       'Response body is : ' + resp_body.to_str())

    def test_request_privacy_edge_proc_fail400(self):
        """Test case for invalid request_privacy_edge_proc request: HTTP 400

        Execute function on private data
        """
        with open(pathlib.Path(__file__).parent / "data/priv_edge_proc_req_def.json") as req:
            body = PrivateExecutionRequestBody.from_dict(json.load(req))
        body.metadata = ""
        response = self.client.open(
            '/requestPrivacyEdgeProc',
            method='POST',
            data=json.dumps(body),
            content_type='application/json')
        self.assertStatus(response, 400,
                          'Response body is : ' + response.data.decode('utf-8'))

    def test_request_privacy_edge_proc_fail401(self):
        """Test case for invalid request_privacy_edge_proc request: HTTP 401

        Execute function on private data
        """
        with open(pathlib.Path(__file__).parent / "data/priv_edge_proc_req_def.json") as req:
            body = PrivateExecutionRequestBody.from_dict(json.load(req))
        body.token = ""
        response = self.client.open(
            '/requestPrivacyEdgeProc',
            method='POST',
            data=json.dumps(body),
            content_type='application/json')
        self.assertStatus(response, 401,
                          'Response body is : ' + response.data.decode('utf-8'))

    def test_request_privacy_edge_proc_fail403(self):
        """Test case for invalid request_privacy_edge_proc request: HTTP 403

        Execute function on private data
        """
        with open(pathlib.Path(__file__).parent / "data/priv_edge_proc_req_def.json") as req:
            body = PrivateExecutionRequestBody.from_dict(json.load(req))
        body.consent += "-restricted"
        response = self.client.open(
            '/requestPrivacyEdgeProc',
            method='POST',
            data=json.dumps(body),
            content_type='application/json')
        self.assertStatus(response, 403,
                          'Response body is : ' + response.data.decode('utf-8'))

    def test_request_privacy_edge_proc_fail404(self):
        """Test case for invalid request_privacy_edge_proc request: HTTP 404

        Execute function on private data
        """
        with open(pathlib.Path(__file__).parent / "data/priv_edge_proc_req_def.json") as req:
            body = PrivateExecutionRequestBody.from_dict(json.load(req))
        body.private_data = ""
        response = self.client.open(
            '/requestPrivacyEdgeProc',
            method='POST',
            data=json.dumps(body),
            content_type='application/json')
        self.assertStatus(response, 404,
                          'Response body is : ' + response.data.decode('utf-8'))

    def test_request_privacy_edge_proc_fail408(self):
        """Test case for invalid request_privacy_edge_proc request: HTTP 408

        Execute function on private data
        """
        with open(pathlib.Path(__file__).parent / "data/priv_edge_proc_req_def.json") as req:
            body = PrivateExecutionRequestBody.from_dict(json.load(req))
        body.metadata['timeout'] = 0
        response = self.client.open(
            '/requestPrivacyEdgeProc',
            method='POST',
            data=json.dumps(body),
            content_type='application/json')
        self.assertStatus(response, 408,
                          'Response body is : ' + response.data.decode('utf-8'))

    def test_request_privacy_edge_proc_fail412(self):
        """Test case for invalid request_privacy_edge_proc request: HTTP 412

        Execute function on private data
        """
        with open(pathlib.Path(__file__).parent / "data/priv_edge_proc_req_def.json") as req:
            body = PrivateExecutionRequestBody.from_dict(json.load(req))
        body.metadata['privacy-zone'] = "zone-B"
        response = self.client.open(
            '/requestPrivacyEdgeProc',
            method='POST',
            data=json.dumps(body),
            content_type='application/json')
        self.assertStatus(response, 412,
                          'Response body is : ' + response.data.decode('utf-8'))

    def test_request_privacy_edge_proc_fail503(self):
        """Test case for invalid request_privacy_edge_proc request: HTTP 503

        Execute function on private data
        """
        with open(pathlib.Path(__file__).parent / "data/priv_edge_proc_req_def.json") as req:
            body = PrivateExecutionRequestBody.from_dict(json.load(req))
        body.metadata['CPU-demand'] = 100
        response = self.client.open(
            '/requestPrivacyEdgeProc',
            method='POST',
            data=json.dumps(body),
            content_type='application/json')
        self.assertStatus(response, 503,
                          'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest

    unittest.main()
