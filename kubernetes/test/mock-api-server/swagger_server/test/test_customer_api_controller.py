# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.models.execution_request_body import ExecutionRequestBody  # noqa: E501
from swagger_server.models.execution_result import ExecutionResult  # noqa: E501
from swagger_server.models.private_execution_request_body import PrivateExecutionRequestBody  # noqa: E501
from swagger_server.models.private_execution_result import PrivateExecutionResult  # noqa: E501
from swagger_server.test import BaseTestCase

from swagger_server.test.examples import EXAMPLE_EDGE_PROC_REQ, EXAMPLE_PRIV_EDGE_PROC_REQ

class TestCustomerAPIController(BaseTestCase):
    """CustomerAPIController integration test stubs"""

    def test_request_edge_proc(self):
        """Test case for request_edge_proc

        Execute function on data
        """
        body = ExecutionRequestBody.from_dict(EXAMPLE_EDGE_PROC_REQ)
        response = self.client.open(
            '/requestEdgeProc',
            method='POST',
            data=json.dumps(body),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_request_privacy_edge_proc(self):
        """Test case for request_privacy_edge_proc

        Execute function on private data
        """
        body = PrivateExecutionRequestBody.from_dict(EXAMPLE_PRIV_EDGE_PROC_REQ)
        response = self.client.open(
            '/requestPrivacyEdgeProc',
            method='POST',
            data=json.dumps(body),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
