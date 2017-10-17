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
from aex_accounts.models import Collection
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
        cdman.set_repository_info('repoUrl1', 'master1', 'token1', 'username', 'password')
        self.assertEqual('master1', cdman._repo_info.branch)
        self.assertEqual('token1', cdman._repo_info.git_token)
        self.assertEqual('repoUrl1', cdman._repo_info.url)
        self.assertEqual('username', cdman._repo_info._private_repo_username)
        self.assertEqual('password', cdman._repo_info._private_repo_password)
        cdman.set_repository_info(None, None, None, None, None)
        self.assertEqual(None, cdman._repo_info.branch)
        self.assertEqual(None, cdman._repo_info.git_token)
        self.assertEqual(None, cdman._repo_info.url)
        self.assertEqual(None, cdman._repo_info._private_repo_username)
        self.assertEqual(None, cdman._repo_info._private_repo_password)

    @patch("vsts_cd_manager.continuous_delivery_manager.ContinuousDelivery")
    @patch("vsts_cd_manager.continuous_delivery_manager.Account")
    def test_setup_continuous_delivery___create_account(self, mock_account, mock_cd):
        # Mock the CD Client
        mocked_cd = mock_cd.return_value
        mocked_cd.provisioning_configuration.return_value = self._get_provisioning_config('queued', '')
        mocked_cd.get_provisioning_configuration.return_value = self._get_provisioning_config('succeeded', '')
        # Mock the Account Client
        mocked_account = mock_account.return_value
        mocked_account.create_account.return_value = Collection('111', 'collection111')
        mocked_account.account_exists.return_value = False
        # create CD manager
        cdman = ContinuousDeliveryManager(None)
        # Mock the vsts info call
        cdman._get_vsts_info = self._mock_get_vsts_info
        # set required values
        cdman.set_azure_web_info('group1', 'web1', 'fakeCreds', 'sub1', 'subname1', 'tenant1', 'South Central US')
        cdman.set_repository_info('repoUrl1', 'master1', 'token1', None, None)
        
        cd_app_type = 'AspNet'
        app_type_details = self.create_cd_app_type_details_map(cd_app_type, None, None, None, None)

        # call setup
        result = cdman.setup_continuous_delivery('staging', app_type_details, "https://account1.visualstudio.com", True, 'token2', None, None)
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

        # call setup
        mocked_account.create_account.return_value = Collection(None, 'collection111')        
        with self.assertRaises(RuntimeError) as context:
            cdman.setup_continuous_delivery('staging', app_type_details, "https://account1.visualstudio.com", True, 'token2', None, None)
        self.assertTrue('Account creation failed' in str(context.exception))

    def test_get_provisioning_configuration_target(self):
        cdman = ContinuousDeliveryManager(None)
        cdman.set_azure_web_info('group1', 'web1', 'fakeCreds', 'sub1', 'subname1', 'tenant1', 'South Central US')
        target = cdman.get_provisioning_configuration_target('authInfo', 'staging', 'test1', None)
        self.assertEqual(target[0].authorization_info, 'authInfo')
        self.assertEqual(target[0].environment_type, 'production')
        self.assertEqual(target[0].friendly_name, 'Production')
        self.assertEqual(target[0].location, 'South Central US')
        self.assertEqual(target[0].provider, 'azure')
        self.assertEqual(target[0].resource_group_name, 'group1')
        self.assertEqual(target[0].resource_identifier, 'web1')
        self.assertEqual(target[0].subscription_id, 'sub1')
        self.assertEqual(target[0].target_type, 'windowsAppService')
        self.assertEqual(target[0].tenant_id, 'tenant1')
        self.assertEqual(target[0].slot_swap_configuration.slot_name, 'staging')
        self.assertEqual(target[1].authorization_info, 'authInfo')
        self.assertEqual(target[1].environment_type, 'test')
        self.assertEqual(target[1].friendly_name, 'Load Test')
        self.assertEqual(target[1].location, 'South Central US')
        self.assertEqual(target[1].provider, 'azure')
        self.assertEqual(target[1].resource_group_name, 'group1')
        self.assertEqual(target[1].resource_identifier, 'test1')
        self.assertEqual(target[1].slot_swap_configuration, None)
        self.assertEqual(target[1].subscription_id, 'sub1')
        self.assertEqual(target[1].subscription_name, 'subname1')
        self.assertEqual(target[1].target_type, 'windowsAppService')
        self.assertEqual(target[1].tenant_id, 'tenant1')

    def test_build_configuration(self):
        # create CD manager
        cdman = ContinuousDeliveryManager(None)
        cd_app_type = None
        nodejs_task_runner = None
        python_framework = None
        python_version = None
        app_working_dir = None
        test_case_count = 8
        for i in range(test_case_count):
            cd_app_type, nodejs_task_runner, python_framework, python_version, app_working_dir = self._set_build_configuration_variables(i)
            app_type_details = self.create_cd_app_type_details_map(cd_app_type, nodejs_task_runner, python_framework, python_version, app_working_dir)
            if(i<3) : 
                # Verifying build configuration outputs
                build_configuration = cdman._get_build_configuration(app_type_details)
                self.assertEqual(build_configuration.node_type, nodejs_task_runner)
                self.assertEqual(build_configuration.python_framework, python_framework)
                self.assertEqual(build_configuration.working_directory, app_working_dir)
                if(python_version is not None) :
                    self.assertEqual(build_configuration.python_version, python_version.replace(" ", "").replace(".", ""))
                cd_app_type = 'AspNetWap' if cd_app_type == 'AspNet' else cd_app_type     
                self.assertEqual(build_configuration.type, cd_app_type)
            else :
                # Verifying exceptions
                with self.assertRaises(RuntimeError):
                    cdman._get_build_configuration(app_type_details)

    def _set_build_configuration_variables(self, i):
        if(i==0):
            return 'Python', None, 'Django', 'Python 2.7.12 x64', 'app_working_dir'
        elif(i==1):
            return 'NodeJS', 'Gulp', None, None, None
        elif(i==2):
            return 'AspNet', None, None, None, None
        elif(i==3):
            return None, None, None, None, None
        elif(i==4):
            return 'UnacceptedAppType', None, None, None, None
        elif(i==5):
            return 'Python', None, 'UnacceptedFramework', 'Python 2.7.12 x64', None
        elif(i==6):
            return 'Python', 'Django', None, 'UnexpectedVersion', None
        elif(i==7):
            return 'NodeJS', 'UnexpectedNodeJSTaskRunner', None, None, None
    
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

    def create_cd_app_type_details_map(self, cd_app_type, nodejs_task_runner, python_framework, python_version, app_working_dir):
        return {
            'cd_app_type' : cd_app_type,
            'nodejs_task_runner' : nodejs_task_runner,
            'python_framework' : python_framework,
            'python_version' : python_version,
            'app_working_dir' : app_working_dir
        }

if __name__ == '__main__':
    unittest.main()