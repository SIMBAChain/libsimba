import logging

from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from httpx import BasicAuth
from libsimba.auth import AuthProvider
from libsimba.config import settings
from libsimba.schemas import AuthProviderName, AuthToken, ConnectionConfig
from libsimba.utils import async_http_client, http_client


logger = logging.getLogger(__name__)


class KcAuthProvider(AuthProvider):
    def provider(self) -> AuthProviderName:
        return AuthProviderName.KC

    async def login_sync(
        self,
        client_id: str = settings.AUTH_CLIENT_ID,
        client_secret: str = settings.AUTH_CLIENT_SECRET,
        config: ConnectionConfig = None,
    ) -> AuthToken:
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
            "scope": settings.AUTH_SCOPE or "email profile roles web-origins",
        }
        sso_host = "{}/auth/realms/{}/protocol/openid-connect/token".format(
            settings.BASE_AUTH_URL, settings.AUTH_REALM
        )
        with http_client(config=config) as client:
            r = client.post(
                sso_host,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        try:
            resp = r.json()
            r.raise_for_status()
            data = {
                "token": resp["access_token"],
                "type": resp["token_type"],
                "expires": (
                    datetime.utcnow() + timedelta(seconds=int(resp["expires_in"]))
                ),
            }
            return AuthToken(**data)
        except Exception as e:
            logger.warning("[KcAuthProvider] :: Error fetching token: {}".format(e))
            raise e

    async def login(
        self,
        client_id: str = settings.AUTH_CLIENT_ID,
        client_secret: str = settings.AUTH_CLIENT_SECRET,
        config: ConnectionConfig = None,
    ) -> AuthToken:
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
            "scope": settings.SCOPE or "email profile roles web-origins",
        }
        try:
            sso_host = "{}/auth/realms/{}/protocol/openid-connect/token".format(
                settings.AUTH_BASE_URL, settings.AUTH_REALM_ID
            )
            async with async_http_client(config=config) as client:
                r = client.post(
                    sso_host,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                resp = r.json()
                r.raise_for_status()
            data = {
                "token": resp["access_token"],
                "type": resp["token_type"],
                "expires": (
                    datetime.utcnow() + timedelta(seconds=int(resp["expires_in"]))
                ),
            }
            return AuthToken(**data)
        except Exception as e:
            logger.warning("[KcAuthProvider] :: Error fetching token: {}".format(e))
            raise e


class BlocksAuthProvider(AuthProvider):
    def provider(self) -> AuthProviderName:
        return AuthProviderName.BLK

    async def login(
        self,
        client_id: str = settings.AUTH_CLIENT_ID,
        client_secret: str = settings.AUTH_CLIENT_SECRET,
        config: ConnectionConfig = None,
    ) -> AuthToken:
        try:
            auth = BasicAuth(client_id, client_secret)
            data = {"grant_type": "client_credentials"}
            async with async_http_client(config=config) as client:
                token_response = await client.post(
                    "{}/o/token/".format(settings.AUTH_BASE_URL),
                    data=data,
                    auth=auth,
                )
                token_response.raise_for_status()
                resp = token_response.json()
            data = {
                "token": resp["access_token"],
                "type": resp["token_type"],
                "expires": (
                    datetime.utcnow() + timedelta(seconds=int(resp["expires_in"]))
                ),
            }
            return AuthToken(**data)
        except Exception as e:
            logger.warning("[BlocksAuthProvider] :: Error fetching token: {}".format(e))
            raise e

    def login_sync(
        self,
        client_id: str = settings.AUTH_CLIENT_ID,
        client_secret: str = settings.AUTH_CLIENT_SECRET,
        config: ConnectionConfig = None,
    ) -> AuthToken:
        try:
            auth = BasicAuth(client_id, client_secret)
            data = {"grant_type": "client_credentials"}
            with http_client(config=config) as client:
                token_response = client.post(
                    "{}/o/token/".format(settings.AUTH_BASE_URL),
                    data=data,
                    auth=auth,
                )
                token_response.raise_for_status()
                resp = token_response.json()
            data = {
                "token": resp["access_token"],
                "type": resp["token_type"],
                "expires": (
                    datetime.utcnow() + timedelta(seconds=int(resp["expires_in"]))
                ),
            }
            return AuthToken(**data)
        except Exception as e:
            logger.warning("[BlocksAuthProvider] :: Error fetching token: {}".format(e))
            raise e


class ClientCredentials(AuthProvider):
    def __init__(self):
        self.registry: Dict[AuthProviderName, AuthProvider] = {}
        ad = BlocksAuthProvider()
        kc = KcAuthProvider()
        self.registry[ad.provider()] = ad
        self.registry[kc.provider()] = kc

    def do_login(self, client_id: str) -> Tuple[Optional[AuthToken], AuthProvider]:
        provider = self.registry.get(settings.AUTH_PROVIDER)
        if not provider:
            raise ValueError(
                f"No provider found for provider type: {settings.AUTH_PROVIDER}"
            )
        token = self.get_cached_token(client_id=client_id)
        return token, provider

    def login_sync(
        self,
        client_id: str = settings.AUTH_CLIENT_ID,
        client_secret: str = settings.AUTH_CLIENT_SECRET,
        config: ConnectionConfig = None,
    ) -> AuthToken:
        token, provider = self.do_login(client_id=client_id)
        if not token:
            token = provider.login_sync(
                client_id=client_id,
                client_secret=client_secret,
                config=config,
            )
        self.cache_token(client_id=client_id, token=token)
        return token

    async def login(
        self,
        client_id: str = settings.AUTH_CLIENT_ID,
        client_secret: str = settings.AUTH_CLIENT_SECRET,
        config: ConnectionConfig = None,
    ) -> AuthToken:
        token, provider = self.do_login(client_id=client_id)
        if not token:
            token = await provider.login(
                client_id=client_id, client_secret=client_secret, config=config
            )
        self.cache_token(client_id=client_id, token=token)
        return token
