FROM ptx-edge/rest-api:0.1
LABEL maintainer="czentye@tmit.bme.hu"
#WORKDIR /usr/src/app
COPY test-requirements.txt setup.py tox.ini ./
RUN python3 -m pip install --no-cache-dir -U -r test-requirements.txt && mkdir -p report
CMD ["tox", "-v", "--", "--with-xunit", \
                        "--xunit-file=report/test-report-mock-api.xml", \
                        "--xunit-testsuite-name=ptx-edge-mock-api"]