# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
from __future__ import print_function
import unittest

from continuous_delivery.models import CiResult

from continuous_delivery.models import CiArtifact

from continuous_delivery.models import CiConfiguration

from continuous_delivery.models import ProvisioningConfigurationSource

from continuous_delivery.models import ProvisioningConfiguration
from mock import patch, Mock
from vsts_accounts.models import AccountModel
from vsts_info_provider.models import TeamProjectInfo, RepositoryInfo, CollectionInfo, VstsInfo
from vsts_cd_manager.continuous_delivery_manager import ContinuousDeliveryManager


class TestContinousDeliveryManager(unittest.TestCase):
    def fake_callback(self):
        pass

    def test_constructor(self):
        cdman = ContinuousDeliveryManager(None)
        cdman = ContinuousDeliveryManager(self.fake_callback)

    def test_get_vsts_app_id(self):
        cdman = ContinuousDeliveryManager(None)
        self.assertEqual('499b84ac-1321-427f-aa17-267ca6975798', cdman.get_vsts_app_id())

    def test_set_azure_web_info(self):
        cdman = ContinuousDeliveryManager(None)
        cdman.set_azure_web_info('group1', 'web1', 'fakeCreds', 'sub1', 'subname1', 'tenant1', 'South Central US')
        self.assertEqual('fakeCreds', cdman._azure_info.credentials)
        self.assertEqual('group1', cdman._azure_info.resource_group_name)
        self.assertEqual('sub1', cdman._azure_info.subscription_id)
        self.assertEqual('subname1', cdman._azure_info.subscription_name)
        self.assertEqual('tenant1', cdman._azure_info.tenant_id)
        self.assertEqual('South Central US', cdman._azure_info.webapp_location)
        self.assertEqual('web1', cdman._azure_info.website_name)
        cdman.set_azure_web_info(None, None, None, None, None, None, None)
        self.assertEqual(None, cdman._azure_info.credentials)
        self.assertEqual(None, cdman._azure_info.resource_group_name)
        self.assertEqual(None, cdman._azure_info.subscription_id)
        self.assertEqual(None, cdman._azure_info.subscription_name)
        self.assertEqual(None, cdman._azure_info.tenant_id)
        self.assertEqual(None, cdman._azure_info.webapp_location)
        self.assertEqual(None, cdman._azure_info.website_name)

    def test_set_repository_info(self):
        cdman = ContinuousDeliveryManager(None)
        cdman.set_repository_info('repoUrl1', 'master1', 'token1')
        self.assertEqual('master1', cdman._repo_info.branch)
        self.assertEqual('token1', cdman._repo_info.git_token)
        self.assertEqual('repoUrl1', cdman._repo_info.url)
        cdman.set_repository_info(None, None, None)
        self.assertEqual(None, cdman._repo_info.branch)
        self.assertEqual(None, cdman._repo_info.git_token)
        self.assertEqual(None, cdman._repo_info.url)

    @patch("vsts_cd_manager.continuous_delivery_manager.ContinuousDelivery")
    @patch("vsts_cd_manager.continuous_delivery_manager.Account")
    def test_setup_continuous_delivery___account_doesnt_exist(self, mock_account, mock_cd):
        # Mock the CD Client
        mocked_cd = mock_cd.return_value
        # Mock the Account Client
        mocked_account = mock_account.return_value
        mocked_account.create_account.return_value = AccountModel()
        mocked_account.account_exists.return_value = False
        # create CD manager
        cdman = ContinuousDeliveryManager(None)
        # Mock the vsts info call
        cdman._get_vsts_info = self._mock_get_vsts_info
        # set required values
        cdman.set_azure_web_info('group1', 'web1', 'fakeCreds', 'sub1', 'subname1', 'tenant1', 'South Central US')
        cdman.set_repository_info('repoUrl1', 'master1', 'token1')
        # call setup
        with self.assertRaises(RuntimeError) as context:
            cdman.setup_continuous_delivery('staging', 'AspNetWap', "account1", False, 'token2')
        self.assertTrue('does not exist' in str(context.exception))

    @patch("vsts_cd_manager.continuous_delivery_manager.ContinuousDelivery")
    @patch("vsts_cd_manager.continuous_delivery_manager.Account")
    def test_setup_continuous_delivery___create_account(self, mock_account, mock_cd):
        # Mock the CD Client
        mocked_cd = mock_cd.return_value
        mocked_cd.provisioning_configuration.return_value = self._get_provisioning_config('queued', '')
        mocked_cd.get_provisioning_configuration.return_value = self._get_provisioning_config('succeeded', '')
        # Mock the Account Client
        mocked_account = mock_account.return_value
        mocked_account.create_account.return_value = AccountModel('111', 'collection111')
        mocked_account.account_exists.return_value = False
        # create CD manager
        cdman = ContinuousDeliveryManager(None)
        # Mock the vsts info call
        cdman._get_vsts_info = self._mock_get_vsts_info
        # set required values
        cdman.set_azure_web_info('group1', 'web1', 'fakeCreds', 'sub1', 'subname1', 'tenant1', 'South Central US')
        cdman.set_repository_info('repoUrl1', 'master1', 'token1')
        
        cd_app_type = 'AspNetWap'
        app_type_details = AppTypeDetails(cd_app_type, None, None, None)

        # call setup
        result = cdman.setup_continuous_delivery('staging', app_type_details, "account1", True, 'token2')
        self.assertEqual('SUCCESS', result.status)
        self.assertTrue("The Team Services account 'https://account1.visualstudio.com' was created" in result.status_message)
        self.assertEqual('https://portal.azure.com/#resource/subscriptions/sub1/resourceGroups/group1/providers/Microsoft.Web/sites/web1/vstscd', result.azure_continuous_delivery_url)
        self.assertEqual('group1', result.azure_resource_group)
        self.assertEqual('sub1', result.azure_subscription_id)
        self.assertEqual('web1', result.azure_website_name)
        self.assertEqual(True, result.vsts_account_created)
        self.assertEqual('https://account1.visualstudio.com', result.vsts_account_url)
        self.assertEqual('https://account1.visualstudio.com/333/_build?_a=simple-process&definitionId=123', result.vsts_build_def_url)
        self.assertEqual('https://account1.visualstudio.com/333/_apps/hub/ms.vss-releaseManagement-web.hub-explorer?definitionId=321&_a=releases', result.vsts_release_def_url)

    def test_build_configuration(self):
        # create CD manager
        cdman = ContinuousDeliveryManager(None)
        cd_app_type = None
        nodejs_task_runner = None
        python_framework = None
        python_version = None
        test_case_count = 8
        for i in range(test_case_count):
            cd_app_type, nodejs_task_runner, python_framework, python_version = self._set_build_configuration_variables(i, cd_app_type, nodejs_task_runner, python_framework, python_version)
            app_type_details = AppTypeDetails(cd_app_type, nodejs_task_runner, python_framework, python_version)
            if(i<3) : 
                # Verifying build configuration outputs
                build_configuration = cdman._get_build_configuration(app_type_details, None)                
                self.assertEqual(build_configuration.type, cd_app_type)
                self.assertEqual(build_configuration.node_type, nodejs_task_runner)
                self.assertEqual(build_configuration.python_framework, python_framework)
                self.assertEqual(build_configuration.python_version, python_version)
            else :
                # Verifying exceptions
                with self.assertRaises(RuntimeError):
                    cdman._get_build_configuration(app_type_details, None)

    def _set_build_configuration_variables(self, i, cd_app_type, nodejs_task_runner, python_framework, python_version):
        if(i==0):
            return 'Python', None, 'Django', 'Python 2.7.12 x64'
        elif(i==1):
            return 'NodeJS', 'Gulp', None, None
        elif(i==2):
            return 'AspNetWap', None, None, None
        elif(i==3):
            return None, None, None, None
        elif(i==4):
            return 'UnacceptedAppType', None, None, None
        elif(i==5):
            return 'Python', None, 'UnacceptedFramework', 'Python 2.7.12 x64'
        elif(i==6):
            return 'Python', 'Django', None, 'UnexpectedVersion'
        elif(i==7):
            return 'NodeJS', 'UnexpectedNodeJSTaskRunner', None, None
    
    def _mock_get_vsts_info(self, vsts_repo_url, cred):
        collection_info = CollectionInfo('111', 'collection111', 'https://collection111.visualstudio.com')
        project_info = TeamProjectInfo('333', 'project1', 'https://collection111.visualstudio.com/project1', 'good', '1')
        repository_info = RepositoryInfo('222', 'repo222', 'https://collection111.visualstudio.com/project1/_git/repo222', project_info)
        return VstsInfo('server1', collection_info, repository_info)

    def _get_provisioning_config(self, status, status_message):
        ci_config = CiConfiguration(
            CiArtifact('333', 'project1', 'https://collection111.visualstudio.com/project1'),
            CiArtifact('123', 'builddef123', 'https://collection111.visualstudio.com/project1/build/definition/123'),
            CiArtifact('321', 'releasedef321', 'https://collection111.visualstudio.com/project1/release/definition/321'),
            CiResult(status, status_message))
        return ProvisioningConfiguration('abcd', None, None, ci_config)

# Copy of the AppTypeDetails class in azure-cli-appservice\azure\cli\command_modules\appservice\custom.py
class AppTypeDetails(object):
    def __init__(self, cd_app_type, nodejs_task_runner, python_framework, python_version):
        self.cd_app_type = cd_app_type
        self.nodejs_task_runner = nodejs_task_runner
        self.python_framework = python_framework
        self.python_version = python_version

if __name__ == '__main__':
    unittest.main()