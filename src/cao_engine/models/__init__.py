"""CAO data models conforming to SETU v2.0 patterns."""

from .arbeidsvoorwaarden import (
    ADVRegeling,
    ArbeidsVoorwaarden,
    Onkostenvergoeding,
    PensioenRegeling,
    Toeslag,
    VerlofRegel,
)
from .cao_document import CAODocument, ProcessingInfo
from .cao_metadata import CAOMetadata, CAOPartij
from .events import CAOEvent, CAOEventType
from .inlenersbeloning import InlenersbeloningElement, InlenersbeloningElementen
from .loongebouw import FunctieGroep, LeeftijdsLoon, Loongebouw, Schaal, Trede
from .momenten import Moment, MomentCategorie, MomentenSet, MomentType
from .subscriptions import CAOSubscription, Subscriber

__all__ = [
    "ADVRegeling",
    "ArbeidsVoorwaarden",
    "CAODocument",
    "CAOEvent",
    "CAOEventType",
    "CAOMetadata",
    "CAOPartij",
    "CAOSubscription",
    "FunctieGroep",
    "InlenersbeloningElement",
    "InlenersbeloningElementen",
    "LeeftijdsLoon",
    "Loongebouw",
    "Moment",
    "MomentCategorie",
    "MomentenSet",
    "MomentType",
    "Onkostenvergoeding",
    "PensioenRegeling",
    "ProcessingInfo",
    "Schaal",
    "Subscriber",
    "Toeslag",
    "Trede",
    "VerlofRegel",
]
