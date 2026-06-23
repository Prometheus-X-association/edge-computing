# Copyright 2025 Janos Czentye
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

import requests

from app.util.config import CONFIG
from app.util.webhook import WebHooKManager

log = logging.getLogger(__name__)

LOGIN_URL = r"http://{host}:{port}/login"
EXCHANGE_URL = r"http://{host}:{port}/consumer/exchange"


def login_to_connector(timeout: int | None = None) -> dict:
    """

    :param timeout:
    :return:
    """
    pdc_host, pdc_port = CONFIG['pdc.host'], int(CONFIG['pdc.port'])
    log.debug(f"Connecting to PDC[{pdc_host}:{pdc_port}]...")
    service_key, secret_key = CONFIG['pdc.key.service'], CONFIG['pdc.key.secret']
    body = {'serviceKey': service_key,
            'secretKey': secret_key}
    log.debug(f"Assembled request body:\n{pprint.pformat(body)}")
    hdr = {'Content-Type': 'application/json',
           'Accept': 'application/json'}
    url = LOGIN_URL.format(host=pdc_host, port=pdc_port)
    log.info(f"Sending POST request to {url}...")
    resp = requests.post(url=url, json=body, headers=hdr, timeout=timeout)
    if resp.status_code != requests.codes.OK:
        log.error(f"Failed to login to PDC: {resp.status_code}")
        resp.raise_for_status()
    log.info("Login to PDC was successful!")
    log.debug(f"Response body:\n{pprint.pformat(resp.json())}")
    return resp.json().get('content')


def make_data_exchange(exchange: str, token: str, timeout: int | None = None) -> dict | None:
    """

    :param exchange:
    :param token:
    :param timeout:
    :return:
    """
    pdc_host, pdc_port = CONFIG['pdc.host'], int(CONFIG['pdc.port'])
    log.debug(f"Connecting to PDC[{pdc_host}:{pdc_port}]...")
    body = {"contract": CONFIG[f"ptx.{exchange}.contract"],
            "resourceId": CONFIG[f"ptx.{exchange}.data.offer"],
            "resources": [{"resource": CONFIG[f"ptx.{exchange}.data.resource"]}],
            "purposeId": CONFIG[f"ptx.{exchange}.service.offer"],
            "purposes": [{"resource": CONFIG[f"ptx.{exchange}.service.resource"]}]}
    log.debug(f"Assembled request body:\n{pprint.pformat(body)}")
    hdr = {'Content-Type': 'application/json',
           'Accept': 'application/json',
           'Authorization': f"Bearer {token}"}
    webhook_data = None
    with WebHooKManager(timeout=timeout) as mgr:
        url = EXCHANGE_URL.format(host=pdc_host, port=pdc_port)
        log.info(f"Sending POST request to {url}...")
        resp = requests.post(url=url, json=body, headers=hdr, timeout=timeout)
        resp_json = resp.json()
        log.debug(f"Response body:\n{pprint.pformat(resp_json)}")
        if resp.status_code != requests.codes.OK:
            log.error(f"Failed to initiate data exchange: {resp.status_code}")
            mgr.server.abort()
        elif not resp_json['content']['success']:
            log.error(f"Failed to initiate data exchange: {resp_json['content']['dataExchange']['status']}")
            mgr.server.abort()
        else:
            log.info(f"Data exchange initiated successfully!")
            log.info(f"Status: {resp_json['content']['dataExchange']['status']}!")
            log.info("Processing connector response...")
            webhook_data = mgr.wait()
    if webhook_data:
        log.info("Webhook received successfully!")
        log.debug(f"Received data size: {sys.getsizeof(webhook_data)}")
    return webhook_data


def perform_pdc_data_exchange(exchange: str, timeout: int | None = None) -> dict | None:
    """

    :param exchange:
    :param timeout:
    :return:
    """
    log.debug(f"Trying to authenticate to the connector...")
    try:
        tokens = login_to_connector(timeout=timeout)
    except (requests.ConnectionError, requests.HTTPError) as e:
        log.error(f"Failed to login to PDC: {e}")
        return None
    bearer = tokens['token']
    log.debug(f"Assigned token: {bearer}")
    log.info(f"Login to connector was successful!")
    log.info("Initiate data exchange...")
    return make_data_exchange(exchange=exchange, token=bearer, timeout=timeout)
