########################################################################################################################
###                                Default setup configuration - Local Sandbox setup                                 ###
########################################################################################################################
## Values can be overwritten by other scripts in ./creds !!!

### Override global settings by enabling local PTX deployment with PTX core sandbox
#LOCAL_SETUP="true"
#USE_SANDBOX="true"

### Cluster Registry default credentials
REGISTRY_USER="admin"
REGISTRY_SECRET="admin"

### PDC testing keys for sandbox
PDC_DB_NAME="dataspace-connector"
PDC_DB_USER="pdc"
PDC_DB_PASSWORD="pdc"
#
PDC_SERVICE_KEY='dWJUUKH9rYF9wr_UAPb6PQXW9h17G7dzuGCbiDhcyjCGgHzLwBp6QHOQhDg0FFxS24GD8nvw37oe_LOjl7ztNATYiVOd_ZEVHQpV'
PDC_SECRET_KEY='Qh4XvuhSJbOp8nMV1JtibAUqjp3w_efBeFUfCmqQW_Nl8x4t3Sk6fWiK5L05CB3jhKZOgY5JlBSvWkFBHH_6fFhYQZWXNoZxO78x'
PDC_EXCHANGE_TRIGGER_API_KEY="eab121f2b8df177ea0d5c53d764be1007dfdbd1043dd7103329563be19e01e26"

### Local VM gateway setup
GW_DOMAIN="training.k3d.localhost"
GW_PORT=4443

### PTX-edge API default credentials
API_BASIC_USER="admin"
API_BASIC_PASSWORD="admin"

### Mocked datasource API default credentials
DS_API_USER="admin"
DS_API_PASSWORD="admin"
DS_API_INSECURE="true"