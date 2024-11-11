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
		python3.12 -m venv --upgrade-deps .venv && \
		. .venv/bin/activate && \
		python3.12 -m pip install -U -r requirements.txt -r requirements-dev.txt \
		)

dev-local: venv
		. .venv/bin/activate
		fastapi dev --port 8080 --reload app/main.py

# Specification generation

openapi: app/main.py
	./scripts/generate_openapi.py --type yaml
	#./scripts/generate_openapi.py --type json

# Cleanup
clean:
	docker image prune -f
	py3clean -v .
	rm -rf .venv

.PHONY: build run dev venv dev-local clean
.DEFAULT_GOAL := dev
.ONESHELL: dev-local