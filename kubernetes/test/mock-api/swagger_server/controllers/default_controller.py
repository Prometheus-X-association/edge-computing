import http

import flask

from swagger_server.models.version_response import VersionResponse  # noqa: E501


def get_version_version_get():  # noqa: E501
    """Get Version

    Versions of the REST-API component # noqa: E501

    :rtype: VersionResponse
    """
    resp = VersionResponse(api='0.1', framework=flask.__version__)
    return flask.make_response(resp.to_dict(), http.HTTPStatus.OK)
