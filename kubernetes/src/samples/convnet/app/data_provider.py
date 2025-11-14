#!/usr/bin/env python3
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
import pathlib
from urllib.request import urlretrieve

import numpy as np

BUILD_DATA_SRC = os.environ.get('BUILD_DATA_SRC', "https://storage.googleapis.com/tensorflow/tf-keras-datasets/mnist.npz")
BUILD_RAW_FILENAME = pathlib.Path(os.environ.get('BUILD_RAW_FILENAME', "mnist.npz")).resolve()
BUILD_TRIM_RATIO = int(os.environ.get('BUILD_TRIM_RATIO', 100))
BUILD_DATA_DST = pathlib.Path(os.environ.get('BUILD_DATA_DST', "./mnist_train_data.npz")).resolve()


def download_mnist_dataset() -> tuple[np.ndarray, np.ndarray]:
    print("\n@@@ Downloading MNIST dataset...")
    # (x_train, y_train), (x_test, y_test) = keras.datasets.mnist.load_data(path="mnist.npz")
    path, headers = urlretrieve(BUILD_DATA_SRC, BUILD_RAW_FILENAME)
    for name, value in headers.items():
        print(name, value)
    data = np.load(path, allow_pickle=False)
    return data['x_train'], data['y_train']


def preprocess_dataset(data: tuple[np.ndarray, np.ndarray], trim_ratio: int = 1) -> tuple[np.ndarray, np.ndarray]:
    print("\n@@@ Preprocessing raw dataset...")
    # Scale images to the [0, 1] range
    x_train = data[0].astype("float32") / 255
    y_train = data[1]
    # Make sure images have shape (28, 28, 1)
    x_train = np.expand_dims(x_train, -1)
    # Shrink data size
    x_train = x_train[:x_train.shape[0] // trim_ratio]
    y_train = y_train[:y_train.shape[0] // trim_ratio]
    print("Prepared dataset:")
    print("x_train shape:", x_train.shape)
    print("y_train shape:", y_train.shape)
    return x_train, y_train


def store_data(data: tuple[np.ndarray, np.ndarray], dst_path: pathlib.Path | str):
    print(f"\n@@@ Saving data to {dst_path}...\n")
    np.savez(dst_path, x_train=data[0], y_train=data[1], allow_pickle=False)


def prepare_training_data():
    raw_data = download_mnist_dataset()
    processed_data = preprocess_dataset(raw_data, trim_ratio=BUILD_TRIM_RATIO)
    store_data(processed_data, dst_path=BUILD_DATA_DST)


if __name__ == "__main__":
    prepare_training_data()
