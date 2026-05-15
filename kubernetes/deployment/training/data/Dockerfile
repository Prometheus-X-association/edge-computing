FROM python:3.14-alpine
LABEL maintainer="czentye@tmit.bme.hu"
WORKDIR /usr/src/api
ENV PYTHONUNBUFFERED=1
RUN python3 -m pip install --no-cache-dir -U fastapi uvicorn
ARG DOMAIN="datasource.ptx.localhost"
#RUN apk add --no-cache openssl && \
#    mkdir -p .cert && \
#    openssl req -x509 -noenc -days 365 -newkey rsa:4096 -subj "/C=EU/O=PTX/OU=dataspace/CN=${DOMAIN}" \
#                                                            -keyout cert/api-tls.key -out cert/api-tls.cert
COPY ./cert ./cert
COPY api.py ./
EXPOSE 4443
CMD ["uvicorn", "api:app", "--host=0.0.0.0", "--port=4443", "--workers=2", "--access-log", \
                                            "--ssl-keyfile=cert/api-tls.key", "--ssl-certfile=cert/api-tls.cert" ]