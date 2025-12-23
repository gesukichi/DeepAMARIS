import os

class FeatureFlags:
    def __init__(self) -> None:
        self.new_conversation_enabled = self._get_bool("NEW_CONVERSATION", False)
        self.rollback_enabled = self._get_bool("ROLLBACK_ENABLED", True)

    def _get_bool(self, key: str, default: bool) -> bool:
        return os.environ.get(key, str(default)).lower() == "true"
