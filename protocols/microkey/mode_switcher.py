from utils.mode_manager import BaseModeSwitcher

class MicrokeyModeSwitcher(BaseModeSwitcher):

    def handle_command(self, command: str):
        super().handle_command(command)
