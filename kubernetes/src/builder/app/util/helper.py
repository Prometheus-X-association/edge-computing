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
import time

log = logging.getLogger(__package__)

DEF_WAIT_SECONDS = 5


def wait_and_exit(_delay: int = DEF_WAIT_SECONDS):
    """

    :param _delay:
    :return:
    """
    log.warning(f"Waiting for builder to finish[{_delay}s]...")
    time.sleep(_delay)


def get_datasource_scheme(path: str) -> str:
    """

    :param path:
    :return:
    """
    return path.strip().split('://', 1)[0]


def get_datasource_path(path: str) -> str:
    """

    :param path:
    :return:
    """
    return path.strip().split('//', 1)[-1]


def local_copy(src: pathlib.Path | str, dst: pathlib.Path | str, orig_name: str = None) -> pathlib.Path:
    """

    :param src:
    :param dst:
    :param orig_name:
    :return:
    """
    dst = pathlib.Path(dst) if isinstance(dst, str) else dst
    if orig_name and dst.suffix == '':
        dst /= orig_name
    dest_dir = dst.parent if dst.suffix else dst
    dest_dir.mkdir(parents=True, exist_ok=True)
    dst = shutil.copy(src, dst)
    return pathlib.Path(dst).resolve(strict=True)
