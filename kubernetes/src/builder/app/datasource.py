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

from app.connector import login_to_connector, perform_data_exchange
from app.util.helper import local_copy

log = logging.getLogger(__package__)


def collect_data_from_file(src_file: str, dst: str) -> pathlib.Path:
    """
    Collect data from file.

    :param src_file:
    :param dst:
    :return:
    """
    src_file = pathlib.Path(src_file).resolve(strict=True)
    log.info(f"Collecting data from {src_file}...")
    dst_path = local_copy(src=src_file, dst=dst)
    log.debug(f"Copied data bytes: {dst_path.stat().st_size}")
    log.info(f"Data is stored in {dst_path.as_uri()}")
    return dst_path


def collect_data_from_url(url: str, dst: str, timeout: int | None = None) -> pathlib.Path:
    """
    Download data from url.

    :param url:
    :param dst:
    :param timeout:
    :return:
    """
    log.info(f"Downloading data from {url}...")
    src_url = httpx.URL(url)
    with tempfile.NamedTemporaryFile(prefix="builder-data-", dir="/tmp", delete_on_close=False) as tmp:
        client = httpx.Client(http2=True, follow_redirects=True, timeout=timeout)
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


def collect_data_from_ptx(contract_id: str, dst: str) -> pathlib.Path:
    raise NotImplementedError()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    collect_data_from_url("https://github.com/czeni/sample-datasets/raw/refs/heads/main/mnist_train_data.npz", ".")
