FROM alpine:latest
RUN echo 'http://dl-cdn.alpinelinux.org/alpine/v3.9/main/' >> /etc/apk/repositories && \
    echo 'http://dl-cdn.alpinelinux.org/alpine/v3.9/community/' >> /etc/apk/repositories && \
    apk add --no-cache mongodb # Install MongoDB v4.0.5
VOLUME /data/db
RUN mkdir -p /data/db && chown -R mongodb:mongodb /data
ENV HOME=/data/db
USER mongodb
EXPOSE 27017
HEALTHCHECK CMD wget --spider -q http://localhost:27017
CMD ["mongod", "--dbpath=/data/db", "--bind_ip=127.0.0.1", "--port=27017", "--quiet", "--noauth"]