FROM python:3.13-alpine
LABEL maintainer="czentye@tmit.bme.hu"
WORKDIR /usr/src/builder
ENV PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -U -r requirements.txt
COPY ./app ./app
CMD ["python3", "-m", "app"]