FROM debian:12.9-slim
RUN apt-get update && apt-get install -y gnupg curl && \
	curl -fsSL https://www.mongodb.org/static/pgp/server-8.0.asc | gpg -o /usr/share/keyrings/mongodb-server-8.0.gpg --dearmor && \
	echo "deb [ signed-by=/usr/share/keyrings/mongodb-server-8.0.gpg ] http://repo.mongodb.org/apt/debian bookworm/mongodb-org/8.0 main" >/etc/apt/sources.list.d/mongodb-org-8.0.list && \
	apt-get update && apt-get install -y mongodb-database-tools && \
	apt-get purge -y gnupg curl  && \
	apt-get autoremove -y && \
	rm -rf /var/lib/apt/lists/*
VOLUME /data/db
WORKDIR /data
COPY ./*.json ./
CMD [ "/bin/sh", "-c", "mongoimport --host=mongodb-sandbox --db=consumer --collection=infrastructureconfigurations \
                                    --type=json --file=init.consumer.json --jsonArray; \
                        mongoimport --host=mongodb-sandbox --db=infrastructure --collection=infrastructureconfigurations \
                                    --type=json --file=init.infrastructure.json --jsonArray; \
                        mongoimport --host=mongodb-sandbox --db=provider --collection=users \
                                    --type=json --file=init.user.provider.json --jsonArray; \
                        mongoimport --host=mongodb-sandbox --db=consumer --collection=users \
                                    --type=json --file=init.user.consumer.json --jsonArray"]