FROM debian:12.14-slim
ARG MONGO_VER=8.0.23
RUN apt-get update && apt-get install -y gnupg curl && \
	curl -fsSL https://www.mongodb.org/static/pgp/server-8.0.asc | gpg -o /usr/share/keyrings/mongodb-server-8.0.gpg --dearmor && \
	echo "deb [ signed-by=/usr/share/keyrings/mongodb-server-8.0.gpg ] http://repo.mongodb.org/apt/debian bookworm/mongodb-org/8.0 main" >/etc/apt/sources.list.d/mongodb-org-8.0.list && \
	apt-get update && apt-get install -y mongodb-org-server=${MONGO_VER} mongodb-mongosh && \
	apt-get purge -y gnupg  && \
	apt-get autoremove -y && \
	rm -rfv /var/lib/apt/lists/*
VOLUME /data/db
RUN mkdir -p /data/db && chown -R mongodb:mongodb /data
ENV GLIBC_TUNABLES="glibc.pthread.rseq=0"
ENV HOME=/data/db
USER mongodb
COPY --chown=mongodb:mongodb ./scripts/entrypoint.mongodb.sh ./entrypoint.sh
EXPOSE 27017
HEALTHCHECK CMD curl -sSf http://localhost:27017 || exit 1
CMD [ "/bin/bash", "entrypoint.sh" ]