FROM python:3.12-alpine
LABEL maintainer="czentye@tmit.bme.hu"
WORKDIR /usr/src/builder
COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -U -r requirements.txt
COPY builder.py .
ENTRYPOINT ["python3.12", "builder.py"]