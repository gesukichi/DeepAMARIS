from typing import Any, AsyncIterator, List
from typing import Protocol
from domain.conversation.interfaces.ai_service import IAIService, Message

class IStreamingAIService(IAIService, Protocol):
    async def stream_response(self, messages: List[Message]) -> AsyncIterator[Any]:
        ...

class StreamResponse:
    def __init__(self, ai: IStreamingAIService):
        self._ai = ai
    async def run(self, messages: List[Message]) -> AsyncIterator[Any]:
        async for chunk in self._ai.stream_response(messages):
            yield chunk
