FROM ptx-edge/rest-api:1.0
LABEL maintainer="czentye@tmit.bme.hu"
#WORKDIR /usr/src/api
ARG USER
COPY requirements-dev.txt tox.ini tests ./
RUN python3 -m pip install --no-cache-dir -U -r requirements-dev.txt && mkdir -p report
RUN chown -R ${USER}:${USER} .
USER ${USER}:${USER}
CMD ["tox", "-v", "--", "--junit-xml=./report/test-report-rest-api.xml", \
                        "-o", "junit_suite_name=ptx-edge-rest-api"]