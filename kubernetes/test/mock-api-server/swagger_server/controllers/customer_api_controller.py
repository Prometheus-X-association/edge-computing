import connexion
import six

from swagger_server.models.execution_request_body import ExecutionRequestBody  # noqa: E501
from swagger_server.models.execution_result import ExecutionResult  # noqa: E501
from swagger_server.models.private_execution_request_body import PrivateExecutionRequestBody  # noqa: E501
from swagger_server.models.private_execution_result import PrivateExecutionResult  # noqa: E501
from swagger_server import util


def request_edge_proc(body):  # noqa: E501
    """Execute function on data

     # noqa: E501

    :param body: 
    :type body: dict | bytes

    :rtype: ExecutionResult
    """
    if connexion.request.is_json:
        body = ExecutionRequestBody.from_dict(connexion.request.get_json())  # noqa: E501
    return 'do some magic!'


def request_privacy_edge_proc(body):  # noqa: E501
    """Execute function on private data

     # noqa: E501

    :param body: 
    :type body: dict | bytes

    :rtype: PrivateExecutionResult
    """
    if connexion.request.is_json:
        body = PrivateExecutionRequestBody.from_dict(connexion.request.get_json())  # noqa: E501
    return 'do some magic!'
