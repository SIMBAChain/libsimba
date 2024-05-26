#  Copyright (c) 2024 SIMBA Chain Inc. https://simbachain.com
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#  THE SOFTWARE.
import json
import logging
import os

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from httpx import BasicAuth
from libsimba.auth import AuthProvider
from libsimba.config import settings
from libsimba.schemas import AuthProviderName, AuthToken, ConnectionConfig, Login
from libsimba.utils import Path, async_http_client, build_url, http_client


logger = logging.getLogger(__name__)


class ClientCredentials(AuthProvider):

    header = "Authorization"

    def __init__(self, do_init: bool = True):
        self.access_tokens: Dict[str, AuthToken] = {}
        if do_init:
            self.registry: Dict[AuthProviderName, AuthProvider] = {}
            ad = BlocksAuthProvider()
            kc = KcAuthProvider()
            pc = PlatformAuthProvider()
            self.registry[ad.provider()] = ad
            self.registry[kc.provider()] = kc
            self.registry[pc.provider()] = pc

    def do_login(
        self, client_id: str, auth_provider: Optional[AuthProviderName] = None
    ) -> Tuple[Optional[AuthToken], AuthProvider]:
        provider_name = auth_provider or settings().AUTH_PROVIDER
        provider = self.registry.get(provider_name)
        if not provider:
            raise ValueError(f"No provider found for provider type: {provider}")
        token = self.get_cached_token(client_id=client_id)
        return token, provider

    def add_header(self, token: AuthToken, headers: Dict[str, Any]) -> None:
        headers[self.header] = f"{token.type} {token.token}"

    def login_sync(
        self,
        login: Login,
        headers: Dict[str, Any],
        config: ConnectionConfig = None,
    ) -> Optional[AuthToken]:
        if not headers.get(self.header):
            token, provider = self.do_login(
                client_id=login.client_id, auth_provider=login.provider
            )
            if not token:
                token = provider.login_sync(
                    login=login,
                    headers=headers,
                    config=config,
                )
            self.add_header(token=token, headers=headers)
            self.cache_token(client_id=login.client_id, token=token)
            return token

    async def login(
        self,
        login: Login,
        headers: Dict[str, Any],
        config: ConnectionConfig = None,
    ) -> Optional[AuthToken]:
        if not headers.get(self.header):
            token, provider = self.do_login(
                client_id=login.client_id, auth_provider=login.provider
            )
            if not token:
                token = await provider.login(
                    login=login,
                    headers=headers,
                    config=config,
                )
            self.add_header(token=token, headers=headers)
            self.cache_token(client_id=login.client_id, token=token)
            return token

    def token_expired(self, token: AuthToken, offset: int = 60) -> bool:
        """
        Checks to see if a token has expired, by checking the 'expires' key
        Adds an offset to allow for delays when performing auth processes

        :param token: the token to check for expiry. Should contain an 'expires' key
        :param offset: To allow for delays in auth processes, this number of seconds is added to the expiry time
        :return:
        """

        now_w_offset = datetime.now(tz=timezone.utc) + timedelta(seconds=offset)
        expiry = token.expires
        if now_w_offset >= expiry:
            logger.debug(
                "[libsimba] :: token_expired : Saved token expires within 60 seconds"
            )
            return True
        logger.debug(
            "[libsimba] :: token_expired : Saved token valid for at least 60 seconds"
        )
        return False

    def cache_token(self, client_id: str, token: AuthToken) -> None:
        """
        Saves the token data to a file if configured, and also memory..

        Checks the TOKEN_DIR environment variable for alternative token storage locations,
        otherwise uses the current working path

        Creates the token directory if it doesn't already exist.

        Adds an "expires" key to the auth token data, set to time "now" added to the expires_in time
        This is used later to discover if the token has expired

        Token files are named <client_id>_token.json

        :param client_id: The ID for the client, token files are named <client_id>_token.json
        :param token: The token object to save
        :return:
        """
        logger.debug(f"[libsimba] :: cache_token : client id: {client_id}")
        if settings().WRITE_TOKEN_TO_FILE:
            token_dir = settings().TOKEN_DIR
            os.makedirs(token_dir, exist_ok=True)
            token_file = os.path.join(token_dir, "{}_token.json".format(client_id))
            with open(token_file, "w") as t1:
                json_data = token.model_dump_json()
                t1.write(json_data)
                logger.debug(
                    "[libsimba] :: cache_token : Saved token : {}".format(token_file)
                )
        self.access_tokens[client_id] = token

    def get_cached_token(self, client_id: str) -> Optional[AuthToken]:
        logger.debug(f"[libsimba] :: get_cached_token : client id: {client_id}")
        """
        Checks memory and a local directory for a file containing an auth token
        If present, check the token hasn't expired, otherwise return it

        Checks the TOKEN_DIR environment variable for alternative token storage locations,
        otherwise uses the current working path

        Token files are named <client_id>_token.json

        :param client_id: The ID for the client, token files are named <client_id>_token.json
        :return: an AuthToken, retrieved from the token file.
        """
        token = self.access_tokens.get(client_id)
        if token:
            if self.token_expired(token):
                self.access_tokens.pop(client_id, None)
            else:
                return token
        if not settings().WRITE_TOKEN_TO_FILE:
            return None
        token_dir = settings().TOKEN_DIR or "./"
        os.makedirs(token_dir, exist_ok=True)
        if os.path.isdir(token_dir):
            token_file = os.path.join(token_dir, "{}_token.json".format(client_id))
            if os.path.isfile(token_file):
                with open(token_file, "r") as t1:
                    token_data = json.load(t1)
                    logger.debug(
                        "[libsimba] :: get_cached_token : Found saved token : {}".format(
                            token_file
                        )
                    )
                token = AuthToken(**token_data)
                if self.token_expired(token):
                    os.remove(token_file)
                    return None
                return token

    def test_token_valid(self, token: AuthToken) -> bool:
        whoami_url = build_url(settings().API_BASE_URL, Path.WHOAMI, {})
        try:
            with http_client() as client:
                r = client.get(
                    whoami_url,
                    headers={"Authorization": "Bearer {}".format(token.token)},
                )
                if r.status_code != 200:
                    return False
                return True
        except:
            return False

    async def test_token_valid_async(self, token: AuthToken) -> bool:
        whoami_url = build_url(settings().API_BASE_URL, "user/whoami/", {})
        try:
            async with async_http_client() as client:
                r = await client.get(
                    whoami_url,
                    headers={"Authorization": "Bearer {}".format(token.token)},
                )
                if r.status_code != 200:
                    return False
                return True
        except:
            return False


class KcAuthProvider(ClientCredentials):

    def __init__(self):
        super().__init__(do_init=False)

    def provider(self) -> AuthProviderName:
        return AuthProviderName.KC

    async def login_sync(
        self,
        login: Login,
        headers: Dict[str, Any],
        config: ConnectionConfig = None,
    ) -> Optional[AuthToken]:
        data = {
            "client_id": login.client_id,
            "client_secret": login.client_secret,
            "grant_type": "client_credentials",
            "scope": settings().AUTH_SCOPE or "email profile roles web-origins",
        }
        sso_host = "{}/auth/realms/{}/protocol/openid-connect/token".format(
            settings().AUTH_BASE_URL, settings().AUTH_REALM
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
                    datetime.now(tz=timezone.utc)
                    + timedelta(seconds=int(resp["expires_in"]))
                ),
            }
            return AuthToken(**data)
        except Exception as e:
            logger.warning("[KcAuthProvider] :: Error fetching token: {}".format(e))
            raise e

    async def login(
        self,
        login: Login,
        headers: Dict[str, Any],
        config: ConnectionConfig = None,
    ) -> Optional[AuthToken]:
        data = {
            "client_id": login.client_id,
            "client_secret": login.client_secret,
            "grant_type": "client_credentials",
            "scope": settings().SCOPE or "email profile roles web-origins",
        }
        try:
            sso_host = "{}/auth/realms/{}/protocol/openid-connect/token".format(
                settings().AUTH_BASE_URL, settings().AUTH_REALM
            )
            async with async_http_client(config=config) as client:
                r = await client.post(
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
                    datetime.now(tz=timezone.utc)
                    + timedelta(seconds=int(resp["expires_in"]))
                ),
            }
            return AuthToken(**data)
        except Exception as e:
            logger.warning("[KcAuthProvider] :: Error fetching token: {}".format(e))
            raise e


class BlocksAuthProvider(ClientCredentials):

    def __init__(self):
        super().__init__(do_init=False)

    def provider(self) -> AuthProviderName:
        return AuthProviderName.BLK

    async def login(
        self,
        login: Login,
        headers: Dict[str, Any],
        config: ConnectionConfig = None,
    ) -> Optional[AuthToken]:
        try:
            auth = BasicAuth(login.client_id, login.client_secret)
            data = {"grant_type": "client_credentials"}
            async with async_http_client(config=config) as client:
                token_response = await client.post(
                    "{}/o/token/".format(settings().AUTH_BASE_URL),
                    data=data,
                    auth=auth,
                )
                token_response.raise_for_status()
                resp = token_response.json()
            data = {
                "token": resp["access_token"],
                "type": resp["token_type"],
                "expires": (
                    datetime.now(tz=timezone.utc)
                    + timedelta(seconds=int(resp["expires_in"]))
                ),
            }
            return AuthToken(**data)
        except Exception as e:
            logger.warning("[BlocksAuthProvider] :: Error fetching token: {}".format(e))
            raise e

    def login_sync(
        self,
        login: Login,
        headers: Dict[str, Any],
        config: ConnectionConfig = None,
    ) -> Optional[AuthToken]:
        try:
            auth = BasicAuth(login.client_id, login.client_secret)
            data = {"grant_type": "client_credentials"}
            with http_client(config=config) as client:
                token_response = client.post(
                    "{}/o/token/".format(settings().AUTH_BASE_URL),
                    data=data,
                    auth=auth,
                )
                token_response.raise_for_status()
                resp = token_response.json()
            data = {
                "token": resp["access_token"],
                "type": resp["token_type"],
                "expires": (
                    datetime.now(tz=timezone.utc)
                    + timedelta(seconds=int(resp["expires_in"]))
                ),
            }
            return AuthToken(**data)
        except Exception as e:
            logger.warning("[BlocksAuthProvider] :: Error fetching token: {}".format(e))
            raise e


class PlatformAuthProvider(ClientCredentials):

    def __init__(self):
        super().__init__(do_init=False)

    def provider(self) -> AuthProviderName:
        return AuthProviderName.PLAT

    async def login(
        self,
        login: Login,
        headers: Dict[str, Any],
        config: ConnectionConfig = None,
    ) -> Optional[AuthToken]:
        try:
            data = {
                "grant_type": "client_credentials",
                "client_id": login.client_id,
                "client_secret": login.client_secret,
            }
            async with async_http_client(config=config) as client:
                token_response = await client.post(
                    f"{settings().AUTH_BASE_URL}/oauth/token",
                    data=data,
                )
                token_response.raise_for_status()
                resp = token_response.json()
            data = {
                "token": resp["access_token"],
                "type": resp["token_type"],
                "expires": datetime.fromtimestamp(resp["expires_at"], tz=timezone.utc),
            }
            return AuthToken(**data)
        except Exception as e:
            logger.warning(
                "[PlatformAuthProvider] :: Error fetching token: {}".format(e)
            )
            raise e

    def login_sync(
        self,
        login: Login,
        headers: Dict[str, Any],
        config: ConnectionConfig = None,
    ) -> Optional[AuthToken]:
        try:
            data = {
                "grant_type": "client_credentials",
                "client_id": login.client_id,
                "client_secret": login.client_secret,
            }
            with http_client(config=config) as client:
                token_response = client.post(
                    f"{settings().AUTH_BASE_URL}/oauth/token",
                    data=data,
                )
                token_response.raise_for_status()
                resp = token_response.json()
            data = {
                "token": resp["access_token"],
                "type": resp["token_type"],
                "expires": datetime.fromtimestamp(resp["expires_at"], tz=timezone.utc),
            }
            return AuthToken(**data)
        except Exception as e:
            logger.warning(
                "[PlatformAuthProvider] :: Error fetching token: {}".format(e)
            )
            raise e
