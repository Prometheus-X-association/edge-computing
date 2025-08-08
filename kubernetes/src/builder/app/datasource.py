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
import pathlib
import tempfile

import httpx
import httpx_auth
from httpx_retries import RetryTransport, Retry

from app.ptx.connector import perform_pdc_data_exchange
from app.util.config import CONFIG
from app.util.helper import local_copy, get_resource_scheme, get_resource_path
from app.util.parsers import DataSourceAuth

log = logging.getLogger(__package__)


def collect_data_from_file(src: str, dst: str) -> pathlib.Path:
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


def collect_data_from_url(url: str, dst: str, auth: str | dict = None, timeout: int = None) -> pathlib.Path:
    """
    Download data from url.

    :param url:
    :param dst:
    :param auth:
    :param timeout:
    :return:
    """
    log.info(f"Downloading data from {url}...")
    src_url, dst_path = httpx.URL(url), None
    with tempfile.NamedTemporaryFile(prefix="builder-data-", dir="/tmp", delete_on_close=False) as tmp:
        auth = DataSourceAuth.parse(auth)
        match auth.scheme:
            case None:
                auth = None
            case "basic":
                auth = httpx.BasicAuth(**auth.params)
            case "digest":
                auth = httpx.DigestAuth(**auth.params)
            case custom:
                auth = getattr(httpx_auth, custom)(**auth.params)
        client = httpx.Client(http2=True, follow_redirects=True, auth=auth, timeout=timeout,
                              transport=RetryTransport(retry=Retry(total=5, backoff_factor=1)))
        log.info(f"Sending GET request to {url} with auth: {type(auth).__name__}...")
        with client.stream("GET", src_url) as resp:
            if resp.status_code != httpx.codes.OK:
                log.error(f"Failed to collect data: HTTP {resp.status_code}")
                resp.raise_for_status()
            for chunk in resp.iter_bytes():
                tmp.write(chunk)
        data_path = pathlib.Path(tmp.name).resolve(strict=True)
        log.debug(f"Collected data bytes: {data_path.stat().st_size}")
        dst_path = local_copy(src=data_path, dst=dst, orig_name=src_url.path.rsplit("/", maxsplit=1)[-1])
    log.info(f"Data is stored in {dst_path.as_uri()}")
    return dst_path


def collect_data_from_ptx(contract_id: str, dst: str, timeout: int = None):
    """

    :param contract_id:
    :param dst:
    :param timeout:
    :return:
    """
    log.info(f"Acquiring private data based on contract[{contract_id}]...")
    data = perform_pdc_data_exchange(contract_id=contract_id, timeout=timeout)
    if data is None:
        log.error("Private data exchange failed!")
        return None
    else:
        log.info(f"Private data exchange was successful!")
    ##########################################################################################
    data_type, data_content = data['type'], data['content']
    log.info(f"Process received data as type: {data_type}")
    match data_type:
        case 'raw' | 'file':
            with tempfile.NamedTemporaryFile(prefix="builder-data-", dir="/tmp", delete_on_close=False) as tmp:
                log.debug(f"Cache content into {tmp.name}...")
                tmp.write(data_content.encode(encoding=data.get("encoding", "utf-8")))
                dst_path = collect_data_from_file(src=tmp.name, dst=dst)
        case 'url':
            url, auth = data['url'], data.get('auth')
            dst_path = collect_data_from_url(url=url, dst=dst, auth=auth)
        case 'docker':
            raise NotImplementedError
            # TODO - manage authentication params defined in 'data'
        case other:
            raise Exception(f"Unsupported data type: {other}")
    return dst_path


########################################################################################################################

def get_data_resources() -> pathlib.Path:
    """

    :return:
    """
    log.info("Obtaining input data...")
    timeout = CONFIG.get('connection.timeout', 30)
    data_src, data_dst = CONFIG['data.src'], CONFIG['data.dst']
    log.debug(f"Datasource is loaded from configuration: {data_src = }, {data_dst = }")
    match get_resource_scheme(data_src):
        case 'file' | 'local':
            data_path = collect_data_from_file(src=get_resource_path(data_src), dst=get_resource_path(data_dst))
        case 'http' | 'https':
            auth = CONFIG.get('data.auth')
            data_path = collect_data_from_url(url=data_src, dst=get_resource_path(data_dst),
                                              auth=auth, timeout=timeout)
        case 'ptx':
            data_path = collect_data_from_ptx(contract_id=get_resource_path(data_src),
                                              dst=get_resource_path(data_dst),
                                              timeout=timeout)
        case other:
            log.error(f"Unknown data source protocol: {other}")
            data_path = None
    return data_path


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    collect_data_from_url("https://github.com/czeni/sample-datasets/raw/refs/heads/main/mnist_train_data.npz", ".")
