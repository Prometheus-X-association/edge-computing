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
import typing
import uuid

import requests
import urllib3

from app.util.config import CONFIG
from app.util.k8s import K8sLeaderElectorManager
from app.util.webhook import WebHooKManager

log = logging.getLogger(__name__)

BASE_ENDPOINT = r"http://{host}:{port}"
HEALTH_URL = f"{BASE_ENDPOINT}/health"
LOGIN_URL = f"{BASE_ENDPOINT}/login"
CONFIG_URL = f"{BASE_ENDPOINT}/private/configuration"
RELOAD_URL = f"{BASE_ENDPOINT}/private/configuration/reload"
EXCHANGE_URL = f"{BASE_ENDPOINT}/consumer/exchange"


def check_connector_availability(retry: int = 5, timeout: int | None = None) -> bool:
    log.info("Checking connector availability...")
    url = HEALTH_URL.format(host=CONFIG['pdc.host'], port=CONFIG['pdc.port'])
    with requests.Session() as session:
        session.mount(url,
                      requests.sessions.HTTPAdapter(
                          max_retries=urllib3.Retry(total=retry,
                                                    backoff_factor=1)
                      ))
        with session.get(url, timeout=timeout, stream=True) as resp:
            if resp.status_code != requests.codes.ok:
                log.warning(f"Received validation response: HTTP {resp.status_code}")
                resp.raise_for_status()
            log.info(f"Connector validation was successful!")
    return True


def login_to_connector(timeout: int | None = None) -> dict[str, typing.Any]:
    """

    :param timeout:
    :return:
    """
    url = LOGIN_URL.format(host=CONFIG['pdc.host'], port=CONFIG['pdc.port'])
    log.debug(f"Connecting to PDC[{url}]...")
    body = {
        'serviceKey': CONFIG['pdc.key.service'],
        'secretKey': CONFIG['pdc.key.secret']
    }
    log.debug(f"Assembled request body:\n{pprint.pformat(body)}")
    log.info(f"Sending POST request to {url}...")
    resp = requests.post(url=url,
                         json=body,
                         timeout=timeout,
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'})
    if resp.status_code != requests.codes.OK:
        log.error(f"Failed to login to PDC: {resp.status_code}")
        resp.raise_for_status()
    log.info("Login to PDC was successful!")
    log.debug(f"Response body:\n{pprint.pformat(resp.json())}")
    return resp.json().get('content')


def get_connector_configuration(token: str, timeout: int | None = None) -> dict[str, typing.Any]:
    """

    :param token:
    :param timeout:
    :return:
    """
    url = CONFIG_URL.format(host=CONFIG['pdc.host'], port=CONFIG['pdc.port'])
    log.debug(f"Acquiring configuration from PDC[{url}]...")
    log.info(f"Sending GET request to {url}...")
    resp = requests.get(url=url,
                        timeout=timeout,
                        headers={'Accept': 'application/json',
                                 'Authorization': f"Bearer {token}"})
    if resp.status_code != requests.codes.OK:
        log.error(f"Failed to acquire configuration: {resp.status_code}")
        resp.raise_for_status()
    log.info("Login to PDC was successful!")
    log.debug(f"Response body:\n{pprint.pformat(resp.json())}")
    return resp.json()


def update_connector_endpoint(endpoint: str, token: str, timeout: int | None = None) -> bool:
    """

    :param endpoint:
    :param token:
    :param timeout:
    :return:
    """
    cfg = get_connector_configuration(token=token, timeout=timeout)
    if cfg.get('endpoint') == endpoint:
        log.debug(f"PDC has been already configured with endpoint: {endpoint}!")
        return True
    log.debug(f"Updating endpoint {endpoint}...")
    url = CONFIG_URL.format(host=CONFIG['pdc.host'], port=CONFIG['pdc.port'])
    body = {
        "endpoint": endpoint
    }
    log.debug(f"Assembled request body:\n{pprint.pformat(body)}")
    log.debug(f"Set configuration to PDC[{url}]...")
    log.info(f"Sending PUT request to {url}...")
    resp = requests.put(url=url,
                        json=body,
                        timeout=timeout,
                        headers={'Content-Type': 'application/json',
                                 'Accept': 'application/json',
                                 'Authorization': f"Bearer {token}"})
    if resp.status_code != requests.codes.OK:
        log.error(f"Failed set configuration: {resp.status_code}")
        resp.raise_for_status()
    log.info("Login to PDC was successful!")
    log.debug(f"Response body:\n{pprint.pformat(resp.json())}")
    return True


def reload_connector(token: str, timeout: int | None = None) -> bool:
    """

    :param token:
    :param timeout:
    :return:
    """
    url = RELOAD_URL.format(host=CONFIG['pdc.host'], port=CONFIG['pdc.port'])
    log.debug(f"Reload configuration in PDC[{url}]...")
    log.info(f"Sending POST request to {url}...")
    resp = requests.post(url=url,
                         timeout=timeout,
                         headers={'Accept': 'application/json',
                                  'Authorization': f"Bearer {token}"})
    if resp.status_code != requests.codes.OK:
        log.error(f"Failed to reload PDC: {resp.status_code}")
        resp.raise_for_status()
    log.info("PDC was reloaded!")
    log.debug(f"Response body:\n{pprint.pformat(resp.json())}")
    return True


def initiate_data_exchange(exchange: str, token: str, timeout: int | None = None) -> dict | None:
    """

    :param exchange:
    :param token:
    :param timeout:
    :return:
    """
    url = EXCHANGE_URL.format(host=CONFIG['pdc.host'], port=CONFIG['pdc.port'])
    log.debug(f"Initiating data exchange from PDC[{url}]...")
    body = {
        "contract": CONFIG[f"ptx.{exchange}.exchange.contract"],
        "resourceId": CONFIG[f"ptx.{exchange}.exchange.data.offer"],
        "resources": [
            {
                "resource": CONFIG[f"ptx.{exchange}.exchange.data.resource"]
            }
        ],
        "purposeId": CONFIG[f"ptx.{exchange}.exchange.service.offer"],
        "purposes": [
            {
                "resource": CONFIG[f"ptx.{exchange}.exchange.service.resource"]
            }
        ]
    }
    log.debug(f"Assembled request body:\n{pprint.pformat(body)}")
    webhook_data = None
    with WebHooKManager(timeout=timeout) as mgr:
        log.info(f"Sending POST request to {url}...")
        resp = requests.post(url=url,
                             json=body,
                             timeout=timeout,
                             headers={'Content-Type': 'application/json',
                                      'Accept': 'application/json',
                                      'Authorization': f"Bearer {token}"})
        resp_json = resp.json()
        log.debug(f"Response body:\n{pprint.pformat(resp_json)}")
        if resp.status_code != requests.codes.OK:
            log.error(f"Failed to initiate data exchange: {resp.status_code}")
            mgr.server.abort()
        elif not resp_json['content']['success']:
            log.error(f"Failed to initiate data exchange with status: {resp_json['content']['dataExchange']['status']}")
            mgr.server.abort()
        else:
            log.info(f"Data exchange initiated successfully!")
            log.info(f"Exchange status: {resp_json['content']['dataExchange']['status']}")
            log.info("Processing connector response...")
            webhook_data = mgr.wait()
    if webhook_data is not None:
        log.info("Webhook data parsed successfully!")
        log.debug(f"Received webhook data:\n{pprint.pformat(webhook_data)}")
    return webhook_data


def perform_configured_exchange(exchange: str, timeout: int | None = None) -> dict | None:
    """

    :param exchange:
    :param timeout:
    :return:
    """
    log.debug(f"Trying to authenticate to the connector...")
    try:
        tokens = login_to_connector(timeout=timeout)
        bearer = tokens['token']
        log.debug(f"Assigned token: {bearer}")
        #
        # success = update_connector_endpoint(endpoint=BASE_ENDPOINT.format(host=CONFIG['pdc.host'],
        #                                                                   port=CONFIG['pdc.port']),
        #                                     token=bearer,
        #                                     timeout=timeout)
        success = reload_connector(token=bearer,
                                   timeout=timeout)
        if not (success and check_connector_availability(timeout=timeout)):
            return None
    except (requests.ConnectionError, requests.HTTPError) as e:
        log.error(f"Failed to communicate with PDC: {e}")
        return None
    log.info(f"Initiate data exchange[{exchange}]...")
    return initiate_data_exchange(exchange=exchange, token=bearer, timeout=timeout)


def perform_pdc_consumer_exchange(exchange: str, synced: bool, timeout: int | None = None) -> dict | None:
    """

    :param exchange:
    :param synced:
    :param timeout:
    :return:
    """
    if not synced:
        return perform_configured_exchange(exchange=exchange, timeout=timeout)
    log.info("Perform synchronized data exchange...")
    identity = CONFIG.get("pdc.sync.identity", f"{CONFIG.get("app.name")}-{uuid.uuid4().hex[:8]}")
    timeout = timeout if timeout else 60
    mgr = K8sLeaderElectorManager(lock_name=CONFIG['pdc.sync.lock'], identity=identity, timeout=timeout, retry=5)
    with mgr.with_task(perform_configured_exchange, exchange=exchange, timeout=timeout) as mgr:
        return mgr.wait()
