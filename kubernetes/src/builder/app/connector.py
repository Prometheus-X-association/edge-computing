# Copyright 2024 Janos Czentye
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging
import pprint
import sys

import httpx

from app.util.config import CONFIG
from app.util.webhook import WebHooKManager

log = logging.getLogger(__package__)

LOGIN_URL = r"http://{host}:{port}/login"
EXCHANGE_URL = r"http://{host}:{port}/consumer/exchange"
CONTRACT_URI = r"https://{host}:{port}/contracts/{id}"
SERVICE_OFFER_URI = r"https://{host}:{port}/v1/catalog/serviceofferings/{id}"


def login_to_connector(timeout: int = None) -> dict:
    """

    :param timeout:
    :return:
    """
    pdc_host, pdc_port = CONFIG['pdc.host'], CONFIG['pdc.port']
    log.debug(f"Connecting to PDC[{pdc_host}:{pdc_port}]...")
    service_key, secret_key = CONFIG['pdc.key.service'], CONFIG['pdc.key.secret']
    body = {'serviceKey': service_key,
            'secretKey': secret_key}
    log.debug(f"Assembled request body:\n{pprint.pformat(body)}")
    hdr = {'Content-Type': 'application/json',
           'Accept': 'application/json'}
    url = LOGIN_URL.format(host=pdc_host, port=pdc_port)
    log.info(f"Sending POST request to {url}...")
    resp = httpx.post(url=url, json=body, headers=hdr, timeout=timeout)
    if resp.status_code != httpx.codes.OK:
        log.error(f"Failed to login to PDC: {resp.status_code}")
        resp.raise_for_status()
    log.info("Login to PDC was successful!")
    log.debug(f"Response body:\n{pprint.pformat(resp.json())}")
    return resp.json().get('content')


def perform_data_exchange(contract_id: str, token: str, timeout: int = None):
    """

    :param contract_id:
    :param token:
    :param timeout:
    :return:
    """
    pdc_host, pdc_port = CONFIG['pdc.host'], CONFIG['pdc.port']
    log.debug(f"Connecting to PDC[{pdc_host}:{pdc_port}]...")
    contract_host, contract_port = CONFIG['contract.host'], CONFIG['contract.port']
    catalog_host, catalog_port = CONFIG['catalog.host'], CONFIG['catalog.port']
    provider_offer_id, consumer_offer_id = CONFIG['catalog.offer.provider'], CONFIG['catalog.offer.consumer']
    body = {'contract': CONTRACT_URI.format(host=contract_host, port=contract_port, id=contract_id),
            'purposeId': SERVICE_OFFER_URI.format(host=catalog_host, port=catalog_port, id=consumer_offer_id),
            'resourceId': SERVICE_OFFER_URI.format(host=catalog_host, port=catalog_port, id=provider_offer_id)}
    log.debug(f"Assembled request body:\n{pprint.pformat(body)}")
    hdr = {'Content-Type': 'application/json',
           'Accept': '*/*',
           'Authorization': f"Bearer {token}"}
    webhook_data = None
    with WebHooKManager(timeout=5) as mgr:
        url = EXCHANGE_URL.format(host=pdc_host, port=pdc_port)
        log.info(f"Sending POST request to {url}...")
        resp = httpx.post(url=url, json=body, headers=hdr, timeout=timeout)
        if resp.status_code != httpx.codes.OK:
            log.error(f"Failed to initiate data exchange: {resp.status_code}")
            mgr.server.abort()
        else:
            log.info("Data exchange initiated successfully!")
            log.debug(f"Response body:\n{pprint.pformat(resp.json())}")
            log.info("Waiting for private data response...")
            webhook_data = mgr.wait()
    if webhook_data:
        log.info("Data received successfully!")
        log.debug(f"Received data size: {sys.getsizeof(webhook_data)}")
    return webhook_data
