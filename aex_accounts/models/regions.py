
from msrest.serialization import Model

class NameAvailability(Model):
    _attribute_map = {
        'count': {'key': 'count', 'type': 'str'},
        'value': {'key': 'value', 'type': 'RegionDetails'},
    }

    def __init__(self, count=None, value=None):
        self.count = count
        self.value = value