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
import os

from app.datasource import collect_data_from_filesystem, collect_data_from_url


def test_builder_datasource_file():
    collect_data_from_filesystem("file://app/util/helper.py", "file://./dst_file.txt")
    os.remove("./dst_file.txt")


def test_builder_datasource_url():
    collect_data_from_url("https://storage.googleapis.com/tensorflow/tf-keras-datasets/mnist.npz", "./dst_file.txt")
    os.remove("./dst_file.txt")
