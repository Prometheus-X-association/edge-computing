# PTX configs

## PDC setup & launch

```bash
$ git clone https://github.com/Prometheus-X-association/dataspace-connector.git
$ cd dataspace-connector

$ cp .env.sample .env       # required by docker compose
# set NODE_ENV=production
$ cp .env .env.production   # required by connector

$ cp src/config.sample.json src/config.production.json
# set endpoint serviceKey secretKey catalogUri contractUri consentUri 

# (re)build while avoiding error due to permission denied in ./data 
$ sudo rm -rf ./data && docker compose build
$ docker compose up
```

## Sandbox setup & launch

```bash
$ git clone https://github.com/Prometheus-X-association/dataspace-connector.git
$ cd dataspace-connector/sandbox/infrastructure
$ COMPOSE_BAKE=true docker compose build
$ docker compose up
```

## Separate connector

- docker-compose.yml
- .env.production
- config.production.json

```bash
$ cd kubernetes/test/ptx && make setup
```