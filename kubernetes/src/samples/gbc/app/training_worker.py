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

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier

TASK_DATA_SRC = pathlib.Path(os.environ.get('TASK_DATA_SRC', "./olivetti_train_data.npz")).resolve()
TRAIN_ESTIMATORS = int(os.environ.get('TRAIN_ESTIMATOR', 30))
TRAIN_RATE = float(os.environ.get('TRAIN_RATE', 0.2))
TRAIN_DEPTH = int(os.environ.get('TRAIN_DEPTH', 2))
TASK_DATA_DST = pathlib.Path(os.environ.get('TASK_DATA_DST', "./gbc_model.pkl")).resolve()


def load_data(data_path: pathlib.Path | str) -> tuple[np.ndarray, np.ndarray]:
    print(f"\n@@@ Loading data from {data_path}...")
    data = np.load(data_path, allow_pickle=False)
    print("Input data:", data)
    return data["x_train"], data["y_train"]


def create_svm_model() -> GradientBoostingClassifier:
    print("\n@@@ Creating GradientBoostingClassifier model...")
    model = GradientBoostingClassifier(n_estimators=TRAIN_ESTIMATORS, learning_rate=TRAIN_RATE, max_depth=TRAIN_DEPTH,
                                       verbose=2)
    return model


def train_model(model: GradientBoostingClassifier, x_train: np.ndarray,
                y_train: np.ndarray) -> GradientBoostingClassifier:
    print(f"\n@@@ Training model: {model}...")
    model.fit(x_train, y_train)
    print("\nModel training finished.")
    return model


def store_model(model: GradientBoostingClassifier, dst_path: pathlib.Path | str) -> None:
    print(f"\n@@@ Storing trained model into {dst_path}...")
    joblib.dump(model, dst_path)


def execute():
    x_train, y_train = load_data(TASK_DATA_SRC)
    model = create_svm_model()
    model = train_model(model, x_train, y_train)
    store_model(model, dst_path=TASK_DATA_DST)


if __name__ == '__main__':
    execute()
