#!/usr/bin/env bash
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
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Usage: generator.sh [schema_file] [model_file]
#PY_VER=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
PY_VER='3.14'

datamodel-codegen --input="${1}" --input-file-type="openapi" --openapi-scopes="schemas" \
                --formatter="isort" --keep-model-order --schema-version="3.0" --schema-version-mode="strict" \
                --field-constraints --use-annotated --naming-strategy="parent-prefixed" \
                --enum-field-as-literal="one" --capitalize-enum-members \
                --use-field-description --use-field-description-example \
                --enable-version-header --target-python-version="${PY_VER}" \
                --disable-warnings --output "${2}"