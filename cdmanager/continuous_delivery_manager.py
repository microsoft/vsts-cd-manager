# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import re
import time

try:
    from urllib.parse import quote, urlparse
except ImportError:
    from urllib import quote  #pylint: disable=no-name-in-module
    from urlparse import urlparse  #pylint: disable=import-error
from azuretfs import AzureTfs, VstsInfoProvider
from azuretfs.models import (ContinuousDeploymentConfiguration, ResourceConfiguration,
                             SourceConfiguration, SourceRepository, Property, VstsInfo)

# Use this class to setup or remove continuous delivery mechanisms for Azure web sites using VSTS build and release
class ContinuousDeliveryManager(object):
    def __init__(self, progress_callback):
        """
        Use this class to setup or remove continuous delivery mechanisms for Azure web sites using VSTS build and release
        :param progress_callback: method of the form func(count, total, message)
        """
        self._update_progress = progress_callback or self._skip_update_progress
        self._azure_info = _AzureInfo()
        self._repo_info = _RepositoryInfo()

    def get_vsts_app_id(self):
        """
        Use this method to get the 'resource' value for creating an Azure token to be used by VSTS
        :return: App id for VSTS
        """
        return '499b84ac-1321-427f-aa17-267ca6975798'

    def set_azure_web_info(self, resource_group_name, website_name, credentials,
                           subscription_id, subscription_name, tenant_id, webapp_location):
        """
        Call this method before attempting to setup continuous delivery to setup the azure settings
        :param resource_group_name:
        :param website_name:
        :param credentials:
        :param subscription_id:
        :param subscription_name:
        :param tenant_id:
        :param webapp_location:
        :return:
        """
        self._azure_info.resource_group_name = resource_group_name
        self._azure_info.website_name = website_name
        self._azure_info.credentials = credentials
        self._azure_info.subscription_id = subscription_id
        self._azure_info.subscription_name = subscription_name
        self._azure_info.tenant_id = tenant_id
        self._azure_info.webapp_location = webapp_location

    def set_repository_info(self, repo_url, branch, git_token):
        """
        Call this method before attempting to setup continuous delivery to setup the source control settings
        :param repo_url:
        :param branch:
        :param git_token:
        :return:
        """
        self._repo_info.url = repo_url
        self._repo_info.branch = branch
        self._repo_info.git_token = git_token

    def remove_continuous_delivery(self):
        """
        To be Implemented
        :return:
        """
        # TODO: this would be called by appservice web source-control delete
        return

    def setup_continuous_delivery(self, azure_deployment_slot, app_type, vsts_account_name, create_account,
                                  vsts_app_auth_token):
        """
        Use this method to setup Continuous Delivery of an Azure web site from a source control repository.
        :param azure_deployment_slot: the slot to use for deployment
        :param app_type: the type of app that will be deployed. i.e. AspNetWap, AspNetCore, etc.
        :param vsts_account_name:
        :param create_account:
        :param vsts_app_auth_token:
        :return: a message indicating final status and instructions for the user
        """

        app_type = self._get_app_project_type(app_type)
        branch = self._repo_info.branch or 'refs/heads/master'

        # Verify inputs before we start generating tokens
        sourceRepository, account_name, team_project_name = self._get_source_repository(self._repo_info.url,
            self._repo_info.git_token, self._azure_info.credentials)
        self._verify_vsts_parameters(vsts_account_name, sourceRepository)
        vsts_account_name = vsts_account_name or account_name
        cd_project_name = team_project_name or self._azure_info.website_name

        # Create AzureTfs client
        az_tfs = AzureTfs('3.2-preview', None, self._azure_info.credentials)

        # Construct the config body of the continuous delivery call
        account_configuration = ResourceConfiguration(create_account,
                                                      [Property('region', 'CUS'),
                                                       Property('PortalExtensionUsesNewAcquisitionFlows', 'false')],
                                                      vsts_account_name)
        pipeline_configuration = None  # This is not set because we are not the ibiza portal
        project_configuration = ResourceConfiguration(True, [Property('','')], cd_project_name)
        source_configuration = SourceConfiguration(sourceRepository, branch)
        target_configuration = [Property('resourceProperties', app_type),
                                Property('resourceGroup', self._azure_info.resource_group_name),
                                Property('subscriptionId', self._azure_info.subscription_id),
                                Property('subscriptionName', self._azure_info.subscription_name),
                                Property('tenantId', self._azure_info.tenant_id),
                                Property('resourceName', self._azure_info.website_name),
                                Property('deploymentSlot', azure_deployment_slot),
                                Property('location', self._azure_info.webapp_location),
                                Property('AuthInfo', 'Bearer ' + vsts_app_auth_token)]
        test_configuration = [Property('appServicePlan',''),
                              Property('appServicePlanName',''),
                              Property('appServicePricingTier','Premium'),
                              Property('testWebAppLocation', self._azure_info.webapp_location),
                              Property('testWebAppName', self._azure_info.website_name)]
        config = ContinuousDeploymentConfiguration(account_configuration, pipeline_configuration, project_configuration,
                                                   source_configuration, target_configuration, test_configuration)
        # Configure the continuous deliver using VSTS as a backend
        response = az_tfs.configure_continuous_deployment(config)
        if response.status == 'inProgress':
            final_status = self._wait_for_cd_completion(az_tfs, response)
            return self._get_summary(final_status, vsts_account_name, self._azure_info.subscription_id, self._azure_info.resource_group_name, self._azure_info.website_name)
        else:
            raise RuntimeError('Unknown status returned from configure_continuous_deployment: ' + response.status)

    def _verify_vsts_parameters(self, cd_account, sourceRepository):
        # if provider is vsts and repo is not vsts then we need the account name
        if sourceRepository.repository_type in [2, 4] and not cd_account:
            raise RuntimeError('You must provide a value for cd-account since your repo-url is not a VSTS repository.')

    def _get_source_repository(self, uri, token, cred):
        # Determine the type of repository (vstsgit == 1, github == 2, tfvc == 3, externalGit == 4)
        # Find the identifier and set the properties; default to externalGit
        type = 4
        identifier = uri
        properties = []
        account_name = None
        team_project_name = None
        match = re.match(r'[htps]+\:\/\/(.+)\.visualstudio\.com.*\/_git\/(.+)', uri, re.IGNORECASE)
        if match:
            type = 1
            account_name = match.group(1)
            # we have to get the repo id as the identifier
            info = self._get_vsts_info(uri, cred)
            identifier = info.repository_info.id
            team_project_name = info.repository_info.project_info.name
        else:
            match = re.match(r'[htps]+\:\/\/github\.com\/(.+)', uri, re.IGNORECASE)
            if match:
                type = 2
                identifier = match.group(1)
                properties = [Property('accessToken', token)]
            else:
                match = re.match(r'[htps]+\:\/\/(.+)\.visualstudio\.com\/(.+)', uri, re.IGNORECASE)
                if match:
                    type = 3
                    identifier = match.group(2)
                    account_name = match.group(1)
        sourceRepository = SourceRepository(identifier, properties, type)
        return sourceRepository, account_name, team_project_name

    def _get_vsts_info(self, vsts_repo_url, cred):
        vsts_info_client = VstsInfoProvider('3.2-preview', vsts_repo_url, cred)
        return vsts_info_client.get_vsts_info()

    def _get_app_project_type(self, cd_app_type):
        app_type =  '{{\"webAppProjectType\":\"{}\"}}'.format(cd_app_type)
        return app_type

    def _wait_for_cd_completion(self, az_tfs, response):
        # Wait for the configuration to finish and report on the status
        step = 5
        max = 100
        self._update_progress(step, max, 'Setting up VSTS continuous deployment')
        status = az_tfs.get_continuous_deployment_operation(response.id)
        while status.status == 'queued' or status.status == 'inProgress':
            step += 5 if step + 5 < max else 0
            self._update_progress(step, max, 'Setting up VSTS continuous deployment (' + status.status + ')')
            time.sleep(2)
            status = az_tfs.get_continuous_deployment_operation(response.id)
        if status.status == 'failed':
            self._update_progress(max, max, 'Setting up VSTS continuous deployment (FAILED)')
            raise RuntimeError(status.result_message)
        self._update_progress(max, max, 'Setting up VSTS continuous deployment (SUCCEEDED)')
        return status

    def _get_summary(self, final_status, account_name, subscription_id, resource_group_name, website_name):
        summary = '\n'
        step_ids = final_status.deployment_step_ids
        if not step_ids or len(step_ids) == 0: return
        steps = {}
        for property in step_ids:
            steps[property.name] = property.value
        # Add the vsts account info
        account_url = 'https://{}.visualstudio.com'.format(quote(account_name))
        if steps['AccountCreated'] == '0':
            summary += "The VSTS account '{}' was updated to handle the continuous delivery.\n".format(account_url)
        elif steps['AccountCreated'] == '1':
            summary += "The VSTS account '{}' was created to handle the continuous delivery.\n".format(account_url)
        # Add the subscription info
        website_url = 'https://portal.azure.com/#resource/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Web/sites/{}/vstscd'.format(
            quote(subscription_id), quote(resource_group_name), quote(website_name))
        summary += 'You can check on the status of the Azure web site deployment here:\n'
        summary += website_url + '\n'
        return summary

    def _skip_update_progress(self, count, total, message):
        return


class _AzureInfo(object):
    def __init__(self):
        self.resource_group_name = None
        self.website_name = None
        self.credentials = None
        self.subscription_id = None
        self.subscription_name = None
        self.tenant_id = None
        self.webapp_location = None


class _RepositoryInfo(object):
    def __init__(self):
        self.url = None
        self.branch = None
        self.git_token = None
