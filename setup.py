from setuptools import setup, find_packages

NAME = "vsts_sdk"
VERSION = "1.0.0"

# To install the library, run the following
#
# python setup.py install
#
# prerequisite: setuptools
# http://pypi.python.org/pypi/setuptools

REQUIRES = ["msrest>=0.2.0"]

setup(
    name=NAME,
    version=VERSION,
    description="SDK to use the APIs for Team Services",
    author_email="jpricket@microsoft.com",
    url="https://github.com/microsoft/vsts-sdk-for-python",
    keywords=["Microsoft", "VSTS", "Team Services", "SDK", "AzureTfs"],
    install_requires=REQUIRES,
    packages=find_packages(),
    include_package_data=True,
    long_description="""\
    """
)
