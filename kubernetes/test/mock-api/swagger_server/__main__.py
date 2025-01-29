#!/usr/bin/env python3.8
import logging

import connexion

from swagger_server import encoder

logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)


def main():
    app = connexion.App(__name__, specification_dir='./swagger/')
    app.app.json_encoder = encoder.JSONEncoder
    app.add_api('swagger.yaml', arguments={'title': 'PTX Edge Computing REST-API'}, pythonic_params=True)
    app.app.logger.info("The API documentation is available on http://localhost:8080/ptx-edge/v1/ui/")
    app.run(port=8080)


if __name__ == '__main__':
    main()
