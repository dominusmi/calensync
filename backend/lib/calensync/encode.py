from abc import abstractmethod
from datetime import datetime, date
import json
from uuid import UUID


class AugmentedEncoder(json.JSONEncoder):
    def default(self, o: object):
        if isinstance(o, UUID):
            return str(o)

        if isinstance(o, ISerializable):
            return o.serialize()

        if isinstance(o, (datetime, date)):
            return o.isoformat()

        return json.JSONEncoder.default(self, o)


class ISerializable:
    @abstractmethod
    def serialize(self):
        pass
