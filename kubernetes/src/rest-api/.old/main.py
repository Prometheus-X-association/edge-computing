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
from pathlib import Path

from connexion import AsyncApp

app = AsyncApp(__name__, specification_dir='.')
app.add_api("ptx-edge.yaml", arguments={'title': 'PTX Edge Computing REST-API'},
            strict_validation=True, pythonic_params=True, validate_responses=True)

if __name__ == '__main__':
    # Automatic reloading for development purposed,
    # In other case use `uvicorn --host localhost --port 8080 --reload main:app`
    # or `gunicorn -k uvicorn_worker.UvicornWorker -b :8080 -w $((`nproc` * 2)) --access-logfile=- main:app`
    # http://localhost:8080/ptx-edge/v1/ui/
    app.run(f"{Path(__file__).stem}:app", host='127.0.0.1', port=8080)
