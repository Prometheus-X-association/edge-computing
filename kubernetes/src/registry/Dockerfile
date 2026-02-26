# syntax=docker/dockerfile:1
# check=skip=SecretsUsedInArgOrEnv
FROM registry:3
LABEL maintainer="czentye@tmit.bme.hu"
ENV REGISTRY_AUTH=htpasswd \
    REGISTRY_AUTH_HTPASSWD_REALM="Registry Realm" \
    REGISTRY_AUTH_HTPASSWD_PATH=/opt/registry/auth/htpasswd \
    REGISTRY_HTTP_TLS_CERTIFICATE=/opt/registry/auth/server.cert \
    REGISTRY_HTTP_TLS_KEY=/opt/registry/auth/server.key \
    REGISTRY_STORAGE_DELETE_ENABLED=true
COPY ./.certs/auth /opt/registry/auth