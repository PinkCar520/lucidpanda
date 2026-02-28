from abc import ABC, abstractmethod

class BaseChannel(ABC):
    @abstractmethod
    def send(self, title, message, source_url=None, db_id=None):
        pass
