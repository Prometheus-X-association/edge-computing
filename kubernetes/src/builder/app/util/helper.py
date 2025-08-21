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
import pathlib
import shutil
import typing

log = logging.getLogger(__name__)

DEF_WAIT_SECONDS = 5


def get_resource_scheme(path: str) -> str:
    """

    :param path:
    :return:
    """
    return path.strip().split('://', 1)[0].lower()


def get_resource_path(path: str) -> str:
    """

    :param path:
    :return:
    """
    return path.strip().split('://', 1)[-1]


def local_copy(src: pathlib.Path | str, dst: pathlib.Path | str, orig_name: str = None) -> pathlib.Path:
    """

    :param src:
    :param dst:
    :param orig_name:
    :return:
    """
    src = pathlib.Path(src) if isinstance(src, str) else src
    dst = pathlib.Path(dst) if isinstance(dst, str) else dst
    if orig_name and dst.suffix == '':
        dst /= orig_name
    dest_dir = dst.parent if dst.suffix else dst
    dest_dir.mkdir(parents=True, exist_ok=True)
    if src.suffix == '' and src.is_dir():
        dst = shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        dst = shutil.copy2(src, dst, follow_symlinks=False)
    return pathlib.Path(dst).resolve(strict=True)


def deep_filter(data: object, keep: typing.Callable = bool) -> object:
    """

    :param data:
    :param keep:
    :return:
    """
    if isinstance(data, dict):
        return dict(filter(lambda kv: bool(kv[1]), ((k, deep_filter(v, keep)) for k, v in data.items())))
    elif isinstance(data, (list, tuple, set)):
        return type(data)(filter(bool, (deep_filter(v, keep) for v in data)))
    elif keep(data):
        return data
    else:
        return None
