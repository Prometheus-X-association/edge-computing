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
TEMPLATE_DIR=$(readlink -f "$(dirname "$0")")
#PY_VER=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
PY_VER='3.14'

datamodel-codegen --input="${1}" --output "${2}" \
                --input-file-type="openapi" \
                --openapi-scopes="schemas" \
                --schema-version="3.0" \
                --schema-version-mode="strict" \
                --formatter="ruff-format" \
                --use-generic-base-class \
                --use-annotated \
                --use-union-operator \
                --use-specialized-enum \
                --use-standard-collections \
                --use-schema-description \
                --use-field-description \
                --use-field-description-example \
                --use-double-quotes \
                --field-constraints \
                --reuse-model \
                --extra-fields="ignore" \
                --field-type-collision-strategy="rename-type" \
                --naming-strategy="full-path" \
                --enum-field-as-literal="none" \
                --set-default-enum-member \
                --capitalize-enum-members \
                --target-python-version="${PY_VER}" \
                --custom-template-dir="${TEMPLATE_DIR}/template" \
                --additional-imports="typing.ClassVar" \
                --enable-version-header \
                --enable-generated-header-marker \
                --disable-timestamp \
                --disable-warnings