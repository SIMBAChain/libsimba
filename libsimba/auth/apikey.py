from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from libsimba.auth import AuthProvider, AuthProviderName, AuthToken
from libsimba.schemas import ConnectionConfig


class ApiKeyProvider(AuthProvider):
    header = "api-key"

    def provider(self) -> AuthProviderName:
        return AuthProviderName.PLAT

    async def login(
        self,
        client_id: str,
        client_secret: str,
        headers: Dict[str, Any],
        config: ConnectionConfig = None,
    ) -> Optional[AuthToken]:
        if not headers.get(self.header):
            token = AuthToken(
                token=client_secret,
                type="ApiKey",
                # always in the future
                expires=datetime.utcnow() + timedelta(days=1),
            )
            headers[self.header] = client_secret
            return token

    def login_sync(
        self,
        client_id: str,
        client_secret: str,
        headers: Dict[str, Any],
        config: ConnectionConfig = None,
    ) -> Optional[AuthToken]:
        if not headers.get(self.header):
            token = AuthToken(
                token=client_secret,
                type="ApiKey",
                # always in the future
                expires=datetime.utcnow() + timedelta(days=1),
            )
            headers[self.header] = client_secret
            return token
