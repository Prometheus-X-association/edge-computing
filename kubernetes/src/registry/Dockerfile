# syntax=docker/dockerfile:1
# check=skip=SecretsUsedInArgOrEnv
FROM registry:3.0.0
LABEL maintainer="czentye@tmit.bme.hu"
ARG REGISTRY_HTTP_SECRET
ENV REGISTRY_AUTH=htpasswd \
    REGISTRY_AUTH_HTPASSWD_REALM="K3dRegistry" \
    REGISTRY_AUTH_HTPASSWD_PATH=/opt/registry/auth/htpasswd \
    REGISTRY_HTTP_SECRET=${REGISTRY_HTTP_SECRET} \
    REGISTRY_HTTP_TLS_CERTIFICATE=/opt/registry/auth/server.cert \
    REGISTRY_HTTP_TLS_KEY=/opt/registry/auth/server.key \
    REGISTRY_STORAGE_DELETE_ENABLED=true \
    REGISTRY_LOG_LEVEL=info \
    OTEL_TRACES_EXPORTER=none
COPY ./.certs/auth /opt/registry/auth