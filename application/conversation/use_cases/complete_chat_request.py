from typing import Any, List
from domain.conversation.interfaces.ai_service import IAIService, Message

class CompleteChatRequest:
    def __init__(self, ai: IAIService):
        self._ai = ai
    async def run(self, messages: List[Message]) -> Any:
        return await self._ai.generate_response(messages)
