#########################################################
### Default setup configuration - Local Sandbox setup ###
#########################################################
## Values can be overwritten by other scripts in ./creds !!!

### Override global settings by enabling local PTX deployment with PTX core sandbox
#LOCAL_SETUP="true"
#USE_SANDBOX="true"

### Cluster Registry setup
REGISTRY_USER="admin"
REGISTRY_SECRET="admin"

### PDC keys
# Testing keys for sandbox
PDC_SERVICE_KEY='dWJUUKH9rYF9wr_UAPb6PQXW9h17G7dzuGCbiDhcyjCGgHzLwBp6QHOQhDg0FFxS24GD8nvw37oe_LOjl7ztNATYiVOd_ZEVHQpV'
PDC_SECRET_KEY='Qh4XvuhSJbOp8nMV1JtibAUqjp3w_efBeFUfCmqQW_Nl8x4t3Sk6fWiK5L05CB3jhKZOgY5JlBSvWkFBHH_6fFhYQZWXNoZxO78x'
PDC_EXCHANGE_TRIGGER_API_KEY="example-api-key"

### Local Gateway setup
GW_DOMAIN="training.k3d.localhost"
GW_PORT=4443

### PTX-edge API basic authentication
API_BASIC_USER="admin"
API_BASIC_PASSWORD="admin"

### Mocked datasource API authentication
DATASOURCE_USERNAME="admin"
DATASOURCE_PASSWORD="admin"
DATASOURCE_INSECURE="true"