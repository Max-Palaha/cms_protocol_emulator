from abc import ABC, abstractmethod


class BaseModeSwitcher(ABC):
    @abstractmethod
    def handle_command(self, command: str) -> str:
        """
        Process the command string and apply mode change logic.
        Should return a message describing the result of command execution.
        """
        pass
