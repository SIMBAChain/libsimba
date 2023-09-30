#  Copyright (c) 2023 SIMBA Chain Inc. https://simbachain.com
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

import logging
import os

from typing import Optional

from libsimba.schemas import AuthFlow, AuthProviderName
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


logger = logging.getLogger(__name__)

ENV_HOME = "SIMBA_HOME"
ENV_FILENAME = "simbachain.env"
ENV_DEFAULT = ".env"


def get_config_file(root: str) -> Optional[str]:
    if os.path.exists(os.path.join(root, f".{ENV_FILENAME}")):
        return os.path.join(root, f".{ENV_FILENAME}")
    if os.path.exists(os.path.join(root, ENV_FILENAME)):
        return os.path.join(root, ENV_FILENAME)
    return os.path.join(root, ENV_DEFAULT)


def locate_config() -> Optional[str]:
    conf = get_config_file(os.getcwd())
    return (
        conf
        if os.path.exists(conf)
        else get_config_file(os.environ.get(ENV_HOME, os.path.expanduser("~")))
    )


class Settings(BaseSettings):
    API_BASE_URL: str
    """ Base URL of Blocks environment """
    AUTH_BASE_URL: str
    """ Base URL of Auth provider """
    AUTH_FLOW: AuthFlow = AuthFlow.CLIENT_CREDENTIALS
    """ Authentication Flow. Currently fixed to client_credentials """
    AUTH_PROVIDER: AuthProviderName = AuthProviderName.BLK
    """ Auth provider. Blocks and KeyCloak are the options. Defaults to Blocks """
    AUTH_CLIENT_SECRET: str = ""
    """ Auth client secret """
    AUTH_CLIENT_ID: str = ""
    """ Auth client ID """
    AUTH_SCOPE: Optional[str] = None
    """ Optional scope. This is set by auth providers if not given """
    AUTH_REALM: Optional[str] = None
    """ Optional realm ID. Used for KeyCloak """
    WRITE_TOKEN_TO_FILE: bool = True
    """ If set to true, tokens will be cached on the file system. Otherwise they are cached in memory """
    TOKEN_DIR: str = "./"
    """ If WRITE_TOKEN_TO_FILE is true, this should be set to where tokens should be stored."""
    CONNECTION_TIMEOUT: Optional[float] = 5.0
    """ connection timeout in seconds for requests. Default is 5 which is the httpx default"""
    LOG_LEVEL: Optional[str] = None
    """
    Set the log level of the 'libsimba' logger.
    Can be one of 'CRITICAL', 'FATAL', 'ERROR', 'WARNING, 'INFO', 'DEBUG', 'NOTSET'
    If not defined or empty, it is not used.
    """

    @field_validator("AUTH_FLOW")
    def set_auth_flow(cls, v: str) -> str:
        return v.lower()

    @field_validator("API_BASE_URL")
    def set_api_url(cls, v: str) -> str:
        if v.endswith("/"):
            v = v[:-1]
        return v

    @field_validator("AUTH_BASE_URL")
    def set_auth_url(cls, v: str) -> str:
        if v.endswith("/"):
            v = v[:-1]
        return v

    model_config = SettingsConfigDict(env_file = locate_config(), env_prefix="SIMBA_")


settings = Settings()

if __name__ == "__main__":
    print(locate_config())
