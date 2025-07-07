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
import pathlib
import time

import pytest

from app.util.config import load_configuration, DEF_CFG_FILE


def test_builder_cfg():
    cfg = load_configuration(DEF_CFG_FILE)
    assert cfg is not None


def test_builder_missing_cfg():
    with pytest.raises(FileNotFoundError):
        load_configuration(pathlib.Path(f"config_{time.time()}.ini"))
