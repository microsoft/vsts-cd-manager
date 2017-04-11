# coding=utf-8
# --------------------------------------------------------------------------
# Code generated by Microsoft (R) AutoRest Code Generator 1.0.1.0
# Changes may cause incorrect behavior and will be lost if the code is
# regenerated.
# --------------------------------------------------------------------------

from msrest.serialization import Model


class ProvisioningConfigurationTarget(Model):
    _attribute_map = {
        'provider': {'key': 'Provider', 'type': 'str'},
        'target_type': {'key': 'Type', 'type': 'str'},
        'subscription_id': {'key': 'SubscriptionId', 'type': 'str'},
        'subscription_name': {'key': 'SubscriptionName', 'type': 'str'},
        'tenant_id': {'key': 'TenantId', 'type': 'str'},
        'resource_identifier': {'key': 'ResourceIdentifier', 'type': 'str'},
        'resource_group_name': {'key': 'ResourceGroupName', 'type': 'str'},
        'location': {'key': 'Location', 'type': 'str'},
        'friendly_name': {'key': 'FriendlyName', 'type': 'str'},
        'authorization_info': {'key': 'AuthorizaionInfo', 'type': 'AuthorizationInfo'},
        'slot_swap_configuration': {'key': 'SlotSwapConfiguration', 'type': 'SlotSwapConfiguration'},
    }

    def __init__(self, provider=None, target_type=None, subscription_id=None, subscription_name=None, tenant_id=None, 
                 resource_identifier=None, resource_group_name=None, location=None, friendly_name=None, authorization_info=None, 
                 slot_swap_configuration=None):
        self.provider = provider
        self.target_type = target_type
        self.subscription_id = subscription_id
        self.subscription_name = subscription_name
        self.tenant_id = tenant_id
        self.resource_identifier = resource_identifier
        self.resource_group_name = resource_group_name
        self.location = location
        self.friendly_name = friendly_name
        self.authorization_info = authorization_info
        self.slot_swap_configuration = slot_swap_configuration