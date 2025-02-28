FROM python:3.13-alpine
LABEL maintainer="czentye@tmit.bme.hu"
WORKDIR /usr/src/builder
COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -U -r requirements.txt
COPY pyproject.toml .
COPY ./app ./app
CMD ["python3.13", "app/builder.py"]