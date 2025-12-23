from typing import Protocol

class IAuthService(Protocol):
    async def authenticate(self, token: str) -> "User": ...

class User:
    def __init__(self, user_id: str):
        self.id = user_id
