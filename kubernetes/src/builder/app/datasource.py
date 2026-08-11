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
import base64
import logging
import pathlib
import tempfile
import typing

import certifi
import requests
import urllib3
from requests.auth import HTTPBasicAuth, HTTPDigestAuth
from requests_toolbelt.downloadutils import stream
from requests_toolbelt.exceptions import StreamingError

from app.ptx.connector import perform_pdc_consumer_exchange
from app.util.config import CONFIG, SKIPPED
from app.util.helper import local_copy, get_resource_scheme_from_uri, get_resource_path
from app.util.parsers import DataSourceAuth, DataSourceAuthScheme

log = logging.getLogger(__name__)


def collect_data_from_filesystem(src: str, dst: str) -> pathlib.Path:
    """
    Collect data from file.

    :param src:
    :param dst:
    :return:
    """
    src = pathlib.Path(src).resolve(strict=True)
    log.info(f"Collecting data from {src}...")
    dst_path = local_copy(src=src, dst=dst)
    log.debug(f"Copied data bytes: {dst_path.stat().st_size}")
    log.info(f"Data is stored in {dst_path.as_uri()}")
    return dst_path


def collect_data_from_url(url: str, dst: str, auth: DataSourceAuth, timeout: int | None = None,
                          retry: int = 1) -> pathlib.Path | None:
    """
    Download data from url.

    :param url:
    :param dst:
    :param auth:
    :param timeout:
    :param retry:
    :return:
    """
    log.info(f"Downloading data from {url}...")
    log.debug(f"Used authentication: {auth}")
    match auth.scheme:
        case DataSourceAuthScheme.BASIC:
            req_auth = HTTPBasicAuth(username=str(auth.user), password=str(auth.secret))
        case DataSourceAuthScheme.DIGEST:
            req_auth = HTTPDigestAuth(username=str(auth.user), password=str(auth.secret))
        case _:
            raise NotImplementedError
    log.info(f"Sending GET request to {url} with auth method: {type(req_auth).__name__}...")
    dst_path = None
    verify = False if auth.insecure else certifi.where()
    with tempfile.NamedTemporaryFile(mode='wb', prefix="builder-data-", dir="/tmp", delete_on_close=False) as tmp:
        try:
            with requests.Session() as session:
                session.mount(url, requests.sessions.HTTPAdapter(max_retries=urllib3.Retry(total=retry,
                                                                                           backoff_factor=1)))
                with session.get(url, timeout=timeout, auth=req_auth, verify=verify, stream=True) as resp:
                    if resp.status_code != requests.codes.ok:
                        log.warning(f"Received response: HTTP {resp.status_code}")
                        resp.raise_for_status()
                    filename = stream.stream_response_to_file(resp, path=tmp)
        except (requests.HTTPError, requests.Timeout, StreamingError) as e:
            log.error(f"Failed to collect data: {e}")
            return None
        except (requests.ConnectionError, requests.TooManyRedirects) as e:
            log.error(f"Failed to connect to URL: {url} -- {e}")
            return None
        # Force small amount of data to be written into tmp file in any case
        tmp.flush()
        data_path = pathlib.Path(filename).resolve(strict=True)
        log.debug(f"Collected data bytes: {data_path.stat().st_size}")
        dst_path = local_copy(src=data_path, dst=dst, orig_name=url.rsplit("/", maxsplit=1)[-1])
    log.info(f"Data is stored in {dst_path.as_uri()}")
    return dst_path


def collect_data_from_ptx(exchange: str, dst: str, retry: int = 1,
                          timeout: int | None = None) -> dict[str, typing.Any] | None:
    """

    :param exchange:
    :param dst:
    :param retry:
    :param timeout:
    :return:
    """
    log.info(f"Acquiring private data based on PTX contract[{exchange}]...")
    data = perform_pdc_consumer_exchange(exchange=exchange, timeout=timeout)
    # {
    #     "type": ...,
    #     "content": {
    #         "url": ...,
    #         "auth": {
    #             "scheme": ...,
    #             "user": ...,
    #             "secret": ...,
    #             "insecure": ...
    #         }
    #      }
    # }
    if data is None:
        log.error("Private data exchange failed!")
        return None
    else:
        log.info(f"Private data exchange was successful!")
    ##########################################################################################
    data_type, data_content = str(data['type']), data['content']
    log.info(f"Process received data as type: {data_type}")
    match data_type.upper():
        case 'RAW' | 'FILE':
            with tempfile.NamedTemporaryFile(prefix="builder-data-", dir="/tmp", delete_on_close=True) as tmp:
                log.debug(f"Cache content into {tmp.name}...")
                tmp.write(base64.b64decode(data_content.encode(encoding=data.get("encoding", "utf-8"))))
                tmp.flush()
                dst_path = collect_data_from_filesystem(src=tmp.name, dst=dst)
        case 'URL' | 'REST':
            url, auth = data_content.get('url'), DataSourceAuth.parse(data_content.get('auth'))
            dst_path = collect_data_from_url(url=url, dst=dst, auth=auth, retry=retry, timeout=timeout)
        case 'DOCKER':
            raise NotImplementedError
            # TODO - manage authentication params defined in 'data'
        case other:
            raise Exception(f"Unsupported data type: {other}")
    data['content']['data'] = {"path": str(dst_path) if dst_path is not None else None}
    return data


########################################################################################################################

def get_data_resources() -> pathlib.Path | None | SKIPPED:
    """

    :return:
    """
    log.info("Obtaining input data...")
    conn_timeout = int(CONFIG.get('connection.timeout', default=30))
    conn_retry = int(CONFIG.get('connection.retry', default=3))
    data_src, data_dst = CONFIG.get('data.src'), CONFIG.get('data.dst')
    log.debug(f"Datasource is loaded from configuration: {data_src = }, {data_dst = }")
    data_path = None
    if (data_method := CONFIG.get('data.method')) is None:
        data_method = get_resource_scheme_from_uri(data_src)
    if data_method is None:
        log.error("Undefined data collection method!")
        return None
    if (dst := get_resource_path(data_dst)) is None:
        log.warning("Undefined data destination!")
        return None
    match data_method.upper():
        case 'SKIP' | None:
            log.warning("Data collection is skipped!")
            data_path = SKIPPED
        case 'FILE' | 'DIR':
            if (src := get_resource_path(data_src)) is None:
                log.warning("Undefined datasource path!")
            else:
                data_path = collect_data_from_filesystem(src=src, dst=dst)
        case 'HTTP' | 'HTTPS':
            if not data_src:
                log.warning("Undefined datasource url!")
            else:
                auth = DataSourceAuth.parse(CONFIG.get('data.auth'))
                data_path = collect_data_from_url(url=data_src, dst=dst, auth=auth,
                                                  retry=conn_retry, timeout=conn_timeout)
        case 'PTX':
            data_path = collect_data_from_ptx(exchange="data", dst=dst,
                                              retry=conn_retry, timeout=conn_timeout)
        case other:
            log.error(f"Unknown data source method: {other}")
            data_path = None
    return data_path


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    # collect_data_from_url("https://github.com/czeni/sample-datasets/raw/refs/heads/main/mnist_train_data.npz", ".")
    collect_data_from_url("http://localhost:9000/datetime.txt", ".", auth=DataSourceAuth.parse("basic:demo:demo"))
