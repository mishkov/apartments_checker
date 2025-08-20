from abc import ABC, abstractmethod
from typing import Sequence
from lib.models import Listing

class Supplier(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Short unique supplier name, e.g. 'onliner'."""

    @abstractmethod
    def fetch(self) -> Sequence[Listing]:
        """Return newest-first listings for this supplier."""