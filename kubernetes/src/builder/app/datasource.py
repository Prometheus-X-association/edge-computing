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
import shutil
import tempfile

import httpx

log = logging.getLogger(__package__)


def collect_data_from_file(src: str, dst: str) -> pathlib.Path:
    """
    Collect data from file.

    :param src:
    :param dst:
    :return:
    """
    log.info(f"Collecting data from {src}...")
    src_path, dst_path = pathlib.Path(src.split('//', 1)[-1]), pathlib.Path(dst.split('//', 1)[-1])
    shutil.copy(src_path, dst_path)
    data = pathlib.Path(dst_path).resolve()
    log.debug(f"Collected data bytes: {data.stat().st_size}")
    log.info(f"Data is stored in {data.as_uri()}")
    return data


def collect_data_from_url(url: str, dst: str, timeout: int | None = None) -> pathlib.Path:
    """
    Download data from url.

    :param url:
    :param dst:
    :param timeout:
    :return:
    """
    log.info(f"Downloading data from {url}...")
    src_url, dst_path = httpx.URL(url), pathlib.Path(dst.split('//', 1)[-1])
    with tempfile.NamedTemporaryFile() as tmp:
        client = httpx.Client(http2=True, timeout=timeout)
        with client.stream("GET", src_url) as resp:
            if resp.status_code != httpx.codes.OK:
                log.error(f"Failed to collect data: HTTP {resp.status_code}")
                resp.raise_for_status()
            for chunk in resp.iter_bytes():
                tmp.write(chunk)
        data = pathlib.Path(tmp.name).resolve()
        log.debug(f"Collected data bytes: {data.stat().st_size}")
        shutil.move(data, dst_path)
    data = pathlib.Path(dst_path).resolve()
    log.info(f"Data is stored in {data.as_uri()}")
    return data


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    collect_data_from_url("https://storage.googleapis.com/tensorflow/tf-keras-datasets/mnist.npz", "./mnist.npz")
    collect_data_from_file("file://mnist.npz", "file://./mnist_copy.npz")
