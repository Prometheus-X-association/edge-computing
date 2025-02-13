# coding: utf-8
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
import json
import logging

from swagger_server.models.versions_response import VersionsResponse
from swagger_server.test import BaseTestCase


class TestDefaultController(BaseTestCase):
    """DefaultController integration test stubs"""

    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger(self.__class__.__name__)
        super().__init__(*args, **kwargs)

    def create_app(self):
        app = BaseTestCase.create_app(self)
        # app.config['LIVESERVER_PORT'] = 8888
        app.config['LIVESERVER_PORT'] = 0  # Dynamic port selection
        app.config['LIVESERVER_TIMEOUT'] = 3
        return app

    def test_get_versions_versions_get(self):
        """Test case for valid   get_versions response: HTTP 200

        Get Version
        """
        response = self.client.open('ptx-edge/v1/versions', method='GET')
        resp_body = VersionsResponse.from_dict(json.loads(response.data.decode('utf-8')))
        self.logger.debug(f"\nResponse body:\n{resp_body.to_str()}\n")
        self.assert200(response)


if __name__ == '__main__':
    import unittest

    unittest.main()
