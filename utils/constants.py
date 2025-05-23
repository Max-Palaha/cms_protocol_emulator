from pathlib import Path
from enum import Enum


class Receiver(str, Enum):
    TRANSLATOR = "TRANSLATOR"
    CLOUD_SIGNALLING = "CLOUD_SIGNALLING"
    CMS = "CMS"
    CMS_MASXML = "CMS_MASXML"
    CMS_SBN = "CMS_SBN"
    CMS_MANITOU = "CMS_MANITOU"
    CMS_SIA_DCS = "CMS_SIA_DCS"


class ResourceAttachmentStatus(Enum):
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    FAILED = "FAILED"


class EventNum(Enum):
    PING = "0602"
    IMAGE = "0730"


class TranslatorEventTypes(Enum):
    EVENT = "00"
    RECOVERY = "01"
    EVENT_AUTO_RECOVERY = "02"


class SignallingEventTypes(Enum):
    EVENT = "01"
    RECOVERY = "03"


class HubServiceMessage(Enum):
    SERVICE_NOTIFICATION = ("1d", "02")
    EVENT_BINARY_DATA_UPDATE = ("1d", "1e")


LOGS_FILE_PATH = Path("./logs/servers.log")
