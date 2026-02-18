FROM python:3.14-alpine
LABEL maintainer="czentye@tmit.bme.hu"
WORKDIR /usr/src/controller
ENV PYTHONUNBUFFERED=1
ARG NS="ptx-edge"
COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -U -r requirements.txt
COPY ./app ./app
RUN echo "kopf run --debug --dev -n ${NS} /usr/src/controller/app/controller.py" > /usr/bin/run-controller && \
    chmod +x /usr/bin/run-controller
CMD [ "kopf", "run", "--verbose", "--namespace=${NS}", "app/controller.py"]