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
import pathlib

from fastapi import status
from fastapi.testclient import TestClient

from app.main import app

tester = TestClient(app)


def test_request_edge_proc_a_ok():
    """Test case for valid request_edge_proc request: HTTP 202

    Execute function on data
    """
    with open(pathlib.Path(__file__).parent / "data/priv_edge_proc_req_def.json") as req:
        body = json.load(req)
    response = tester.post(url='/ptx-edge/v1/requestPrivacyEdgeProc', json=body)
    assert response.status_code == status.HTTP_202_ACCEPTED


def test_request_edge_proc_fail400():
    """Test case for invalid request_edge_proc request: HTTP 400

    Execute function on data
    """
    with open(pathlib.Path(__file__).parent / "data/priv_edge_proc_req_def.json") as req:
        body = json.load(req)
    body['function'] = ""
    response = tester.post(url='/ptx-edge/v1/requestPrivacyEdgeProc', json=body)
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_request_edge_proc_fail401():
    """Test case for invalid request_edge_proc request: HTTP 403

    Execute function on data
    """
    with open(pathlib.Path(__file__).parent / "data/priv_edge_proc_req_def.json") as req:
        body = json.load(req)
    body['token'] = None
    response = tester.post(url='/ptx-edge/v1/requestPrivacyEdgeProc', json=body)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_request_edge_proc_fail403():
    """Test case for invalid request_edge_proc request: HTTP 403

    Execute function on data
    """
    with open(pathlib.Path(__file__).parent / "data/priv_edge_proc_req_def.json") as req:
        body = json.load(req)
    body['func_contract'] += "-bogus"
    response = tester.post(url='/ptx-edge/v1/requestPrivacyEdgeProc', json=body)
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_request_edge_proc_fail404():
    """Test case for invalid request_edge_proc request: HTTP 404

    Execute function on data
    """
    with open(pathlib.Path(__file__).parent / "data/priv_edge_proc_req_def.json") as req:
        body = json.load(req)
    body['function'] = None
    response = tester.post(url='/ptx-edge/v1/requestPrivacyEdgeProc', json=body)
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_request_edge_proc_fail408():
    """Test case for invalid request_edge_proc request: HTTP 408

    Execute function on data
    """
    with open(pathlib.Path(__file__).parent / "data/priv_edge_proc_req_def.json") as req:
        body = json.load(req)
    body['metadata']['timeout'] = 0
    response = tester.post(url='/ptx-edge/v1/requestPrivacyEdgeProc', json=body)
    assert response.status_code == status.HTTP_408_REQUEST_TIMEOUT


def test_request_edge_proc_fail412():
    """Test case for invalid request_edge_proc request: HTTP 412

    Execute function on data
    """
    with open(pathlib.Path(__file__).parent / "data/priv_edge_proc_req_def.json") as req:
        body = json.load(req)
    body['metadata']['privacy-zone'] = "zone-B"
    response = tester.post(url='/ptx-edge/v1/requestPrivacyEdgeProc', json=body)
    assert response.status_code == status.HTTP_412_PRECONDITION_FAILED


def test_request_edge_proc_fail503():
    """Test case for invalid request_edge_proc request: HTTP 503

    Execute function on data
    """
    with open(pathlib.Path(__file__).parent / "data/priv_edge_proc_req_def.json") as req:
        body = json.load(req)
    body['metadata']['CPU-demand'] = 100
    response = tester.post(url='/ptx-edge/v1/requestPrivacyEdgeProc', json=body)
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
