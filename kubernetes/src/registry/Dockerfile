# syntax=docker/dockerfile:1
# check=skip=SecretsUsedInArgOrEnv
FROM registry:3
LABEL maintainer="czentye@tmit.bme.hu"
ENV REGISTRY_AUTH=htpasswd
ENV REGISTRY_AUTH_HTPASSWD_REALM="Registry Realm"
ENV REGISTRY_AUTH_HTPASSWD_PATH=/opt/registry/auth/htpasswd
ENV REGISTRY_HTTP_TLS_CERTIFICATE=/opt/registry/auth/server.cert
ENV REGISTRY_HTTP_TLS_KEY=/opt/registry/auth/server.key
ENV REGISTRY_STORAGE_DELETE_ENABLED=true
COPY ./.certs/auth /opt/registry/auth