FROM debian:12.9-slim
ARG MONGO_VER=8.0.5
RUN apt-get update && apt-get install -y gnupg curl && \
	curl -fsSL https://www.mongodb.org/static/pgp/server-8.0.asc | gpg -o /usr/share/keyrings/mongodb-server-8.0.gpg --dearmor && \
	echo "deb [ signed-by=/usr/share/keyrings/mongodb-server-8.0.gpg ] http://repo.mongodb.org/apt/debian bookworm/mongodb-org/8.0 main" >/etc/apt/sources.list.d/mongodb-org-8.0.list && \
	apt-get update && apt-get install -y mongodb-org-server=${MONGO_VER} && \
	apt-get purge -y gnupg curl  && \
	apt-get autoremove -y && \
	rm -rf /var/lib/apt/lists/*
VOLUME /data/db
WORKDIR /data
EXPOSE 27017
CMD ["mongod", "--bind_ip", "0.0.0.0"]
