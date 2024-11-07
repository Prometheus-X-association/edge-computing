build:
	docker build -t rest-api .
	docker image prune -f
	docker images --no-trunc rest-api

run:
	docker run --rm --name rest-api -ti -p 8080:8080 rest-api

dev:
	docker run --rm -ti -p 8080:8080 -v ./app:/usr/src/api/app rest-api \
				uvicorn app.main:app --port 8080 --reload --reload-dir app

.PHONY: build run dev
.DEFAULT_GOAL := dev