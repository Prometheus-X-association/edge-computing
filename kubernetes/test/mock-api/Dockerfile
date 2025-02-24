FROM python:3.8-alpine
RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app
COPY requirements.txt /usr/src/app/
RUN python3.8 -m pip install --no-cache-dir -U -r requirements.txt
COPY . /usr/src/app
EXPOSE 8080
CMD ["python3.8", "-m", "swagger_server"]