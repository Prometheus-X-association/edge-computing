# coding: utf-8

from setuptools import setup, find_packages

NAME = "swagger_server"
VERSION = "1.0.0"
# To install the library, run the following
#
# python setup.py install
#
# prerequisite: setuptools
# http://pypi.python.org/pypi/setuptools

REQUIRES = [
    "flask==1.1.4",
    "markupsafe==2.0.1",
    "connexion>=2.6.0,<3.0",
    "swagger-ui-bundle>=0.0.2"
]

setup(
    name=NAME,
    version=VERSION,
    description="PTX Edge Computing REST-API",
    author_email="czentye.janos@vik.bme.hu",
    url="",
    keywords=["Swagger", "PTX Edge Computing REST-API"],
    install_requires=REQUIRES,
    packages=find_packages(),
    package_data={'': ['swagger/swagger.yaml']},
    include_package_data=True,
    entry_points={
        'console_scripts': ['swagger_server=swagger_server.__main__:main']},
    long_description="""\
    The Edge Computing (Decentralized AI processing) BB-02 provides value-added services exploiting an underlying distributed edge computing infrastructure.
    """
)
