FROM ptx-edge/rest-api:1.0
LABEL maintainer="czentye@tmit.bme.hu"
#WORKDIR /usr/src/api
COPY requirements-dev.txt pyproject.toml tox.ini ./
RUN python3 -m pip install --no-cache-dir -U -r requirements-dev.txt
CMD ["pytest", "-v", "--suppress-no-test-exit-code", "--junit-xml=report/report-test-rest-api.xml"]