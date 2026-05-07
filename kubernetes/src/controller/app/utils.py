# Copyright 2026 Janos Czentye
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either expess or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging
import pprint
import typing


def deep_json_filter(data: object, keep: typing.Callable = bool) -> object:
    """

    :param data:
    :param keep:
    :return:
    """
    if isinstance(data, dict):
        return dict(filter(lambda kv: bool(kv[1]), ((k, deep_json_filter(v, keep)) for k, v in data.items())))
    elif isinstance(data, (list, tuple, set)):
        return type(data)(filter(bool, (deep_json_filter(v, keep) for v in data)))
    elif keep(data):
        return data
    else:
        return None


def deep_openapi_filter(data: object, keep: typing.Callable = bool) -> object:
    """

    :param data:
    :param keep:
    :return:
    """
    if hasattr(data, "openapi_types"):
        return dict(filter(lambda kv: bool(kv[1]),
                           ((att, deep_openapi_filter(getattr(data, att), keep)) for att in data.openapi_types)))
    if isinstance(data, dict):
        return dict(filter(lambda kv: bool(kv[1]), ((k, deep_json_filter(v, keep)) for k, v in data.items())))
    elif isinstance(data, (list, tuple, set)):
        return type(data)(filter(bool, (deep_openapi_filter(v, keep) for v in data)))
    elif keep(data):
        return data
    else:
        return None


def sanitize_model(data: object, indent: int = 2) -> str:
    return pprint.pformat(deep_openapi_filter(data), indent=indent)


class ExcludeProbesFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return 'GET /healthz ' not in record.message
