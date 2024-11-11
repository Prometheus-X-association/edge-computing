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
import pathlib

import fastapi

from app import VERSION
from app.model.version import VersionResponse

app = fastapi.FastAPI(title="PTX Edge Computing REST-API",
                      description="The Edge Computing (Decentralized AI processing) BB-02 provides value-added "
                                  "services exploiting an underlying distributed edge computing infrastructure.",
                      contact=dict(email="czentye.janos@vik.bme.hu"),
                      version=VERSION,
                      external_docs=dict(url="https://github.com/Prometheus-X-association/edge-computing",
                                         description="Main project"),
                      servers=[dict(url="/ptx-edge/v1",
                                    description="PTX Edge Computing")],
                      openapi_tags=[dict(name="customerAPI",
                                         description="Customer-facing API (EdgeAPI)"),
                                    dict(name="connectorAPI",
                                         description="Connector-facing API (PrivacyPreservingAPI)"),],
                      redoc_url=None)


@app.get("/version")
async def get_version() -> VersionResponse:
    """Versions of the REST-API component"""
    return VersionResponse(api=VERSION, framework=fastapi.__version__)


if __name__ == '__main__':
    # Automatic reloading for development purposed,
    # In other case use `fastapi dev --host localhost --port 8080 --reload app/main.py`
    # or `fastapi run --port 8080 --workers $((`nproc` * 2)) app/main.py`
    # or `gunicorn -k uvicorn_worker.UvicornWorker -b :8080 -w $((`nproc` * 2)) --access-logfile=- main:app`
    # http://localhost:8080/docs | http://localhost:8080/redoc
    import uvicorn

    uvicorn.run(f"{pathlib.Path(__file__).stem}:app", host='127.0.0.1', port=8080, reload=True, access_log=True)
