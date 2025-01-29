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

# Docker commands
build: Dockerfile
	docker build -t rest-api .
	docker images --no-trunc rest-api

run:
	docker run --rm --name rest-api -ti -p 8080:8080 rest-api

dev:
	docker run --rm --name rest-api -ti -p 8080:8080 -v ./app:/usr/src/api/app rest-api \
				uvicorn app.main:app --port 8080 --reload --reload-dir app


# Local development in venv
venv: requirements.txt
	test -d .venv || (\
		python3.13 -m venv --upgrade-deps .venv && \
		. .venv/bin/activate && \
		python3.13 -m pip install -U -r requirements.txt -r requirements-dev.txt \
		)

dev-local: venv
		(\
		. .venv/bin/activate && \
		fastapi dev --port 8080 --reload app/main.py; \
		)

# Specification generation

openapi: app/main.py
	(\
	. .venv/bin/activate && \
	./scripts/generate_openapi.py --type yaml \
	)

# Cleanup
clean:
	docker image prune -f
	py3clean -v .
	rm -rf .venv

.PHONY: build run dev clean
.DEFAULT_GOAL := dev
#.ONESHELL: dev-local openapi