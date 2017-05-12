Visual Studio Team Services Continuous Delivery Manager
=======================================================

This project provides the class ContinuousDeliveryManager and supporting classes. This CD manager class allows
the caller to manage Azure Continuous Delivery pipelines that are maintained within a VSTS account.

Contribute Code
===============

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/). For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

Packaging
=========

The released packages for this code can be found here https://pypi.python.org/pypi/vsts-cd-manager. 
Use the standard PYPI packaging flow to push a new release. Make sure to increment the version number appropriately.

*Example*
::
    python setup.py sdist
    python -m twine upload dist/*
::

Running Tests
=============
The only class we have unit tests for is the ContinuousDeliveryManager class. As features are added, add tests 
and maintain a high (>80%) code coverage number for this class.
You can run these tests in the following way:
::
    python tests/test_continuous_delivery_manager.py
::

Code Coverage
=============
Code coverage for the vsts_cd_manager.py file should be kept current with any new features. Most of the other code 
is boiler plate REST API code that could be generated for the most part. You can find out more about how to run
code coverage here: https://coverage.readthedocs.io/en/coverage-4.4