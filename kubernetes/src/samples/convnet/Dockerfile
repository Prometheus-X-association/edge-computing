#FROM python:3.12-alpine
FROM python:3.12-slim
LABEL maintainer="czentye@tmit.bme.hu"
WORKDIR /usr/src/worker
#RUN apk add --no-cache g++ cmake build-base hdf5-dev && \
#    python3 -m pip install --no-cache-dir ml-dtypes~=0.5.1 h5py~=3.14.0 optree~=0.16.0
ENV KERAS_BACKEND=jax
COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -U -r requirements.txt
COPY ./app ./app
CMD ["python3", "-m", "app"]