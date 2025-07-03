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

import keras
import numpy as np

# os.environ["KERAS_BACKEND"] = "jax"
TASK_DATA_SRC = pathlib.Path(os.environ.get('TASK_DATA_SRC', "./mnist_train_data.npz")).resolve()
TRAIN_BATCH_SIZE = int(os.environ.get('TRAIN_BATCH_SIZE', 128))
TRAIN_EPOCHS = int(os.environ.get('TRAIN_EPOCHS', 30))
TASK_DATA_DST = pathlib.Path(os.environ.get('TASK_DATA_DST', "./convnet_model.keras")).resolve()


def load_data(data_path: pathlib.Path | str) -> tuple[np.ndarray, np.ndarray]:
    print(f"\n@@@ Loading data from {data_path}...")
    data = np.load(data_path, allow_pickle=False)
    print("Input data:", data)
    return data["x_train"], data["y_train"]


def create_convnet_model() -> keras.models.Model:
    print("\n@@@ Creating ConvNet model...")
    model = keras.Sequential([keras.layers.Input(shape=(28, 28, 1)),
                              keras.layers.Conv2D(64, kernel_size=(3, 3), activation="relu"),
                              keras.layers.Conv2D(64, kernel_size=(3, 3), activation="relu"),
                              keras.layers.MaxPooling2D(pool_size=(2, 2)),
                              keras.layers.Conv2D(128, kernel_size=(3, 3), activation="relu"),
                              keras.layers.Conv2D(128, kernel_size=(3, 3), activation="relu"),
                              keras.layers.GlobalAveragePooling2D(),
                              keras.layers.Dropout(0.5),
                              keras.layers.Dense(10, activation="softmax")],
                             name="convnet")
    model.summary()
    model.compile(loss=keras.losses.SparseCategoricalCrossentropy(),
                  optimizer=keras.optimizers.Adam(learning_rate=1e-3),
                  metrics=[keras.metrics.SparseCategoricalAccuracy(name="acc")])
    return model


def train_model(model: keras.models.Model, x_train: np.ndarray, y_train: np.ndarray) -> keras.models.Model:
    print(f"\n@@@ Training model: {model}...")
    model.fit(x_train, y_train,
              batch_size=TRAIN_BATCH_SIZE,
              epochs=TRAIN_EPOCHS,
              validation_split=0.1,
              callbacks=[keras.callbacks.EarlyStopping(monitor="val_loss", patience=2)])
    print("\nModel training finished.")
    return model


def store_model(model: keras.models.Model, dst_path: pathlib.Path | str) -> None:
    print(f"\n@@@ Storing trained model into {dst_path}...")
    model.save(dst_path)


def execute():
    x_train, y_train = load_data(TASK_DATA_SRC)
    model = create_convnet_model()
    model = train_model(model, x_train, y_train)
    store_model(model, dst_path=TASK_DATA_DST)


if __name__ == '__main__':
    execute()
