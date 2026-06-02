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
set -eu

### Considered envvars:
# - MONGO_BIND_IP
# - MONGO_PORT
# - MONGO_INITDB_ROOT_USERNAME
# - MONGO_INITDB_ROOT_PASSWORD
# - PDC_DB_NAME
# - PDC_DB_USER
# - PDC_DB_PASSWORD

# Define user creation commands
CREATE_ADMIN_USER="""
db.createUser({
    user: '${MONGO_INITDB_ROOT_USERNAME:-admin}',
    pwd: '${MONGO_INITDB_ROOT_PASSWORD:-$(openssl rand -base64 32 | tr -d /=+ | cut -c -16)}',
    roles: [
        {role: 'userAdminAnyDatabase', db: 'admin'},
        {role: 'readWriteAnyDatabase', db: 'admin'}
    ]});
"""

DEF_DB_NAME="dataspace-connector"
CREATE_PDC_USER="""
db.getSiblingDB('${PDC_DB_NAME:-DEF_DB_NAME}').createUser({
    user: '${PDC_DB_USER:-pdc}',
    pwd: '${PDC_DB_PASSWORD:-pdc}',
    roles: [
        {role: 'readWrite', db: '${PDC_DB_NAME:-DEF_DB_NAME}'}
    ]});
"""

# Create admin and PDC users in running mongo process
_RAND_PORT="$(shuf -i '30000-40000' -n1)"
mongod --dbpath=/data/db --port="${_RAND_PORT}" --fork --syslog --noauth
mongosh --port="${_RAND_PORT}" admin --eval "${CREATE_ADMIN_USER}"
mongosh --port="${_RAND_PORT}" admin --eval "${CREATE_PDC_USER}"
mongod --shutdown --syslog

# Use authentication if password is set, not authentication as fallback
AUTH=$(if [ -n "${PDC_DB_PASSWORD:-}" ]; then echo '--auth'; else echo '--noauth'; fi)

# Initiate mongodb server process
set -x
exec mongod --dbpath=/data/db --bind_ip="${MONGO_BIND_IP:-127.0.0.1}" --port="${MONGO_PORT:-27017}" --quiet "${AUTH}" "$@"
