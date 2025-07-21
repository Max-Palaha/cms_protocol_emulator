from abc import ABC, abstractmethod
from utils.mode_manager import mode_manager
from utils.logger import logger


class BaseModeSwitcher(ABC):
    def __init__(self, receiver_name: str):
        self.receiver_name = receiver_name
        self.protocol_mode = mode_manager.get(receiver_name)

    @abstractmethod
    def handle_command(self, command: str):
        pass

    def _invalid_command(self, command: str):
        logger.warning(f"[{self.receiver_name}] Invalid command: {command}")
