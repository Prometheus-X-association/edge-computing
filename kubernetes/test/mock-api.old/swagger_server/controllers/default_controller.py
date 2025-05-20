import http

import flask

from swagger_server.models.versions_response import VersionsResponse  # noqa: E501


def get_versions_versions_get():  # noqa: E501
    """Get Version

    Versions of the REST-API component # noqa: E501

    :rtype: VersionsResponse
    """
    resp = VersionsResponse(api='0.1', framework=flask.__version__)
    return flask.make_response(resp.to_dict(), http.HTTPStatus.OK)
