#FROM python:3.12-alpine
FROM alpine:3.22
LABEL maintainer="czentye@tmit.bme.hu"
WORKDIR /usr/src/worker
ENV PYTHONUNBUFFERED=1
#COPY requirements.txt .
#RUN python3 -m pip install --no-cache-dir -U -r requirements.txt
RUN apk add --no-cache py3-numpy py3-joblib py3-scikit-learn py3-scikit-datasets
COPY ./app ./app
CMD ["python3", "-m", "app"]