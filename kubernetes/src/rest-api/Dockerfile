FROM python:3.13-alpine
LABEL maintainer="czentye@tmit.bme.hu"
WORKDIR /usr/src/api
ENV PYTHONUNBUFFERED=1
COPY requirements.txt pyproject.toml ./
RUN python3 -m pip install --no-cache-dir -U -r requirements.txt
COPY ./app ./app
EXPOSE 8080
#CMD ["fastapi", "run", "--port", "8080", "app/main.py"]
#CMD ["hypercorn", "app.main:app", "-b", "0.0.0.0:8080", "-w", "4"]
#CMD ["granian", "--interface", "asgi", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--opt"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]
