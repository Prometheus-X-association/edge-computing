# swagger_client.CustomerAPIApi

All URIs are relative to */*

Method | HTTP request | Description
------------- | ------------- | -------------
[**request_edge_proc**](CustomerAPIApi.md#request_edge_proc) | **POST** /requestEdgeProc | Execute function on data
[**request_privacy_edge_proc**](CustomerAPIApi.md#request_privacy_edge_proc) | **POST** /requestPrivacyEdgeProc | Execute function on private data

# **request_edge_proc**
> ExecutionResult request_edge_proc(body)

Execute function on data

### Example
```python
from __future__ import print_function
import time
import swagger_client
from swagger_client.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = swagger_client.CustomerAPIApi()
body = swagger_client.ExecutionRequestBody() # ExecutionRequestBody | 

try:
    # Execute function on data
    api_response = api_instance.request_edge_proc(body)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling CustomerAPIApi->request_edge_proc: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**ExecutionRequestBody**](ExecutionRequestBody.md)|  | 

### Return type

[**ExecutionResult**](ExecutionResult.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **request_privacy_edge_proc**
> PrivateExecutionResult request_privacy_edge_proc(body)

Execute function on private data

### Example
```python
from __future__ import print_function
import time
import swagger_client
from swagger_client.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = swagger_client.CustomerAPIApi()
body = swagger_client.PrivateExecutionRequestBody() # PrivateExecutionRequestBody | 

try:
    # Execute function on private data
    api_response = api_instance.request_privacy_edge_proc(body)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling CustomerAPIApi->request_privacy_edge_proc: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**PrivateExecutionRequestBody**](PrivateExecutionRequestBody.md)|  | 

### Return type

[**PrivateExecutionResult**](PrivateExecutionResult.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

