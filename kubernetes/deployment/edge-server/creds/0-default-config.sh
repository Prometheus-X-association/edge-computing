########################################################################################################################
###                                Default setup configuration - Local Sandbox setup                                 ###
########################################################################################################################
## Values can be overwritten by other scripts in ./creds !!!

### Global settings to enable local PTX deployment and PTX core sandbox without NGROK reverse tunnel
LOCAL_SETUP="true"
USE_SANDBOX="true"
USE_NGROK="false"

### NGROK tunneling
#NGROK_AUTHTOKEN=
#NGROK_DOMAIN=
#
#DS_NGROK_AUTHTOKEN=
#DS_NGROK_DOMAIN=

### Cluster Registry default credentials
REGISTRY_USER="admin"
REGISTRY_SECRET="admin"

### PDC
##DS_PDC_DIR="${HOME}/pdc"   # Set separate path to avoid vbox dir sharing issues
#DS_PDC_VER="v1.11.0"

### MongoDB setup for the PDC instances
MONGO_DB_NAME="dataspace-connector"
MONGO_DB_USER="pdc"
MONGO_DB_PASSWORD="pdc"
#
#DS_MONGO_INITDB_ROOT_USERNAME=
#DS_MONGO_INITDB_ROOT_PASSWORD=
##
#DS_MONGO_DB_NAME=
#DS_MONGO_DB_USER=
#DS_MONGO_DB_PASSWORD=

### PDC testing keys for sandbox
PDC_SERVICE_KEY='dWJUUKH9rYF9wr_UAPb6PQXW9h17G7dzuGCbiDhcyjCGgHzLwBp6QHOQhDg0FFxS24GD8nvw37oe_LOjl7ztNATYiVOd_ZEVHQpV'
PDC_SECRET_KEY='Qh4XvuhSJbOp8nMV1JtibAUqjp3w_efBeFUfCmqQW_Nl8x4t3Sk6fWiK5L05CB3jhKZOgY5JlBSvWkFBHH_6fFhYQZWXNoZxO78x'
PDC_EXCHANGE_TRIGGER_API_KEY="eab121f2b8df177ea0d5c53d764be1007dfdbd1043dd7103329563be19e01e26"
#
#DS_PDC_SERVICE_KEY=
#DS_PDC_SECRET_KEY=
#DS_PDC_EXCHANGE_TRIGGER_API_KEY=
##
#DS_PDC_ENDPOINT="https://${DS_NGROK_DOMAIN}"

### Local VM gateway setup
GW_DOMAIN="edge.k3d.localhost"
GW_PORT=4443

### Exposed port of the infrastructure for the cluster viewer
#DS_GW_DOMAIN=
#DS_GW_PORT=

### PTX-edge API default credentials
API_BASIC_USER="admin"
API_BASIC_PASSWORD="admin"

### Demo default credentials
DVA_POSTGRES_CRED="postgres:postgres"

#DS_DATA_FILE=

## Learning commons
#SC_CONTRACT_ID=
## Learning commons - Tutorlink traces -> Edge node -> AI service
#SC_CHAIN_BASIC_ID=
## Tutorlink - Online tutoring sessions and follow-up exercises
#PROVIDER_OFFER_ID=
## Tutorlink - Online tutoring sessions and follow-up exercises - Data
#PROVIDER_RESOURCE_ID=
## xAPI for Research - Learning analytics AI service
#CONSUMER_OFFER_ID=
## xAPI for Research - Learning analytics AI service - Service
#CONSUMER_RESOURCE_ID=