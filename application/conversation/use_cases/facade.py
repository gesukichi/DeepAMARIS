from typing import Any

from application.configuration.feature_flags import FeatureFlags
from application.conversation.use_cases.orchestrate_conversation import (
    ConversationOrchestrator, ConversationRequest,
)

class OldAppFunctions:
    async def conversation_internal(self, request_json) -> Any:
        # Placeholder to represent legacy path. In tests we'll fake this.
        return {"legacy": True, "request": request_json}

class ConversationFacade:
    def __init__(self, flags: FeatureFlags, orchestrator: ConversationOrchestrator, old: OldAppFunctions):
        self._flags = flags
        self._new = orchestrator
        self._old = old

    async def handle_conversation(self, request_json) -> Any:
        if not self._flags.new_conversation_enabled:
            return await self._old.conversation_internal(request_json)
        try:
            req = ConversationRequest(auth_token=request_json.get("auth_token", ""),
                                      messages=request_json.get("messages", []))
            return await self._new.handle(req)
        except Exception:
            if self._flags.rollback_enabled:
                return await self._old.conversation_internal(request_json)
            raise
