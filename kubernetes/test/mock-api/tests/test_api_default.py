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
import httpx
from fastapi.testclient import TestClient

from app.main import app

tester = TestClient(app)


def test_openapi():
    response = tester.get("/ptx-edge/v1/openapi.json")
    assert response.status_code == 200

def test_ui_doc():
    response = tester.get("/ui/")
    assert response.status_code == 200

def test_versions():
    response = tester.get("/versions")
    assert response.status_code == httpx.codes.OK
    data = response.json()
    assert "api" in data and data['api'] is not None
    assert "framework" in data and data['framework'] is not None
