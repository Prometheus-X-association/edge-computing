FROM ptx-edge/rest-api:0.1
LABEL maintainer="czentye@tmit.bme.hu"
#WORKDIR /usr/src/app
COPY test-requirements.txt .
RUN python3 -m pip install --no-cache-dir -U -r test-requirements.txt && mkdir -p report
CMD ["nosetests", "-v", "-w", "swagger_server/test", "--with-xunit", "--xunit-file=report/report-test-mock-api.xml"]