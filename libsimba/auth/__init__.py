import json
import logging
import os

from abc import ABC, abstractmethod
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, Optional

from libsimba.config import settings
from libsimba.schemas import AuthProviderName, AuthToken, ConnectionConfig
from libsimba.utils import Path, async_http_client, build_url, http_client


logger = logging.getLogger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, (datetime, date, time)):
            return obj.isoformat()
        elif isinstance(obj, timedelta):
            return (datetime.min + obj).time().isoformat()

        return super(DateTimeEncoder, self).default(obj)

    def __call__(self, obj: Any) -> Any:
        return self.default(obj)


class AuthProvider(ABC):
    access_tokens: Dict[str, AuthToken] = {}

    def provider(self) -> AuthProviderName:
        return AuthProviderName.NOOP

    @abstractmethod
    async def login(
        self,
        client_id: str = settings.AUTH_CLIENT_ID,
        client_secret: str = settings.AUTH_CLIENT_SECRET,
        config: ConnectionConfig = None,
    ) -> AuthToken:
        """login and return a token"""

    @abstractmethod
    def login_sync(
        self,
        client_id: str = settings.AUTH_CLIENT_ID,
        client_secret: str = settings.AUTH_CLIENT_SECRET,
        config: ConnectionConfig = None,
    ) -> AuthToken:
        """login and return a token"""

    def token_expired(self, token: AuthToken, offset: int = 60) -> bool:
        """
        Checks to see if a token has expired, by checking the 'expires' key
        Adds an offset to allow for delays when performing auth processes

        :param token: the token to check for expiry. Should contain an 'expires' key
        :param offset: To allow for delays in auth processes, this number of seconds is added to the expiry time
        :return:
        """

        now_w_offset = datetime.utcnow() + timedelta(seconds=offset)
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
        if settings.WRITE_TOKEN_TO_FILE:
            token_dir = settings.TOKEN_DIR
            os.makedirs(token_dir, exist_ok=True)
            token_file = os.path.join(token_dir, "{}_token.json".format(client_id))
            with open(token_file, "w") as t1:
                json_data = token.json(encoder=DateTimeEncoder())
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
        if not settings.WRITE_TOKEN_TO_FILE:
            return None
        token_dir = settings.TOKEN_DIR or "./"
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
        whoami_url = build_url(settings.API_BASE_URL, Path.WHOAMI, {})
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
        whoami_url = build_url(settings.API_BASE_URL, "user/whoami/", {})
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
