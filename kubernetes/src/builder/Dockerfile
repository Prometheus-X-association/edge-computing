FROM python:3.14-alpine
LABEL maintainer="czentye@tmit.bme.hu"
WORKDIR /usr/src/builder
RUN apk add --no-cache skopeo~=1.20.1
ENV PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -U -r requirements.txt
COPY ./app ./app
EXPOSE 9999
RUN echo "python3 -m app -v" > /usr/bin/run-builder && chmod +x /usr/bin/run-builder
CMD ["python3", "-m", "app"]