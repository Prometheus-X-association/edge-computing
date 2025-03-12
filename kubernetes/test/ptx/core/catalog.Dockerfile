# Dockerfile for WireMock
FROM wiremock/wiremock:3.12.1-alpine
COPY ./utils/catalog/stubs/ ./mappings
HEALTHCHECK NONE
ENTRYPOINT ["/docker-entrypoint.sh", "--global-response-templating", "--disable-gzip", "--verbose", "--port", "8082"]