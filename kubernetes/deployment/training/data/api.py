# Copyright 2026 Janos Czentye
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
import enum
import os
import pathlib
import secrets
import typing

import uvicorn
from fastapi import FastAPI, HTTPException, status, Depends, APIRouter, Path, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles

__version__ = '1.0.0'

# Main app
app = FastAPI(title="DatasourceAPI", version=__version__, docs_url=None, redoc_url=None)


# For checking API availability
@app.get("/version")
async def version():
    return {"name": app.title, "version": app.version}


# Include datasets from /resource unauthorized to API as fallback static routes
RESOURCE = os.getenv("RESOURCE", "resource")
app.mount("/static", StaticFiles(directory=pathlib.Path(__file__).parent / RESOURCE), name="static")

# Define basic authentication credentials
security = HTTPBasic(realm="DataSource")
USER = os.getenv("USERNAME", "")
PASSWORD = os.getenv("PASSWORD", "")


# Authenticate requests based on user/pass from envvars
def _authenticate_user(creds: typing.Annotated[HTTPBasicCredentials, Depends(security)]):
    if not (secrets.compare_digest(creds.username.encode(), USER.encode())
            and secrets.compare_digest(creds.password.encode(), PASSWORD.encode())):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            headers={"WWW-Authenticate": "Basic"})


# Define protected datasets
PREFIX = os.getenv("PREFIX", "dataset")
datasource = APIRouter(prefix=f"/{PREFIX}", dependencies=[Depends(_authenticate_user)])

Zone = enum.StrEnum("Zone", [p.name for p in pathlib.Path(__file__).parent.joinpath(RESOURCE).iterdir()
                             if p.is_dir() and not p.name.startswith("_") and not p.name.startswith(".")])


@app.exception_handler(RequestValidationError)
async def suppress_validation_error(request: Request, exc: RequestValidationError):
    return PlainTextResponse("Validation error!", status_code=400)


@datasource.get("/{zone}/{data}")
async def get_data(zone: typing.Annotated[Zone, Path()],
                   data: typing.Annotated[str, Path(min_length=1, pattern='^([^/]+)\\.\\w+$')]):
    dataset: pathlib.Path = (pathlib.Path(__file__).parent / RESOURCE / zone.value / data).resolve()
    if not dataset.exists() or not str(dataset).startswith(str(pathlib.Path(__file__).parent)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return FileResponse(dataset, media_type="application/octet-stream")


# Include datasource endpoints to API
app.include_router(datasource)

if __name__ == '__main__':
    # Run API for debugging
    uvicorn.run(f"{pathlib.Path(__file__).stem}:app", host='127.0.0.1', port=8888, reload=True, access_log=True,
                log_level="debug")
