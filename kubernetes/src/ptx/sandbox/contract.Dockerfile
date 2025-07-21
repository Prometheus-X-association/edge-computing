# Dockerfile for WireMock
FROM wiremock/wiremock:3.12.1-alpine
COPY ./utils/contract/stubs/ ./mappings
HEALTHCHECK CMD wget --spider -O /dev/null http://localhost:8081/__admin/health || exit 1
ENTRYPOINT ["/docker-entrypoint.sh", "--global-response-templating", "--disable-gzip", "--verbose", "--port", "8081"]