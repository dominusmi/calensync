from abc import abstractmethod
from datetime import datetime, date
import json
from uuid import UUID


class AugmentedEncoder(json.JSONEncoder):
    def default(self, obj: object):
        if isinstance(obj, UUID):
            return str(obj)

        if isinstance(obj, ISerializable):
            return obj.serialize()

        if isinstance(obj, (datetime, date)):
            return obj.isoformat()

        return json.JSONEncoder.default(self, obj)


class ISerializable:
    @abstractmethod
    def serialize(self):
        pass