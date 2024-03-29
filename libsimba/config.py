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

from logging.config import dictConfig, fileConfig
from typing import Optional, Union

from libsimba.schemas import AuthFlow, AuthProviderName
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    API_BASE_URL: Optional[str] = None
    """ Base URL of Blocks environment """
    AUTH_BASE_URL: Optional[str] = None
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
    CONNECTION_TIMEOUT: float = 5.0
    """ connection timeout in seconds for requests. Default is 5 which is the httpx default"""
    SSL_VERIFY: Union[bool, str] = True
    """ A path to a cert file or false to turn off verification """
    LOG_LEVEL: Optional[str] = None
    """
    Set the log level of the 'libsimba' logger.
    Can be one of 'CRITICAL', 'FATAL', 'ERROR', 'WARNING, 'INFO', 'DEBUG', 'NOTSET'
    If not defined or empty, it is not used.
    """

    @field_validator("AUTH_FLOW")
    def set_auth_flow(cls, v: str) -> str:
        return v.lower()

    @model_validator(mode="after")
    def check_urls(self) -> "Settings":
        api_base = self.API_BASE_URL
        if not api_base:
            api_base = os.environ.get("SIMBA_API_BASE_URL")
        if api_base and api_base.endswith("/"):
            api_base = api_base[:-1]
        self.API_BASE_URL = api_base
        auth_base = self.AUTH_BASE_URL
        if not auth_base:
            auth_base = os.environ.get("SIMBA_AUTH_BASE_URL")
        if auth_base and auth_base.endswith("/"):
            auth_base = auth_base[:-1]
        self.AUTH_BASE_URL = auth_base
        return self

    model_config = SettingsConfigDict(
        env_file=locate_config(), env_prefix="SIMBA_", extra="ignore"
    )


class SettingsObject:
    instance: Optional[Settings] = None


libsimba_settings = SettingsObject()


def settings(**kwargs) -> Settings:
    if libsimba_settings.instance is None:
        log_file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "logging.conf"
        )
        log_file = os.environ.get("SIMBA_LOG_CONFIG", log_file_path)
        if log_file.endswith(".json"):
            with open(log_file) as json_conf:
                dictConfig(json.load(json_conf))
        else:
            fileConfig(log_file)
        # create settings
        libsimba_settings.instance = Settings(**kwargs)
        logger = logging.getLogger("libsimba")
        if libsimba_settings.instance.LOG_LEVEL:
            logger.setLevel(libsimba_settings.instance.LOG_LEVEL)
            for handler in logger.handlers:
                handler.setLevel(libsimba_settings.instance.LOG_LEVEL)

        logger.debug(
            f"[Settings] :: set log level to {libsimba_settings.instance.LOG_LEVEL}"
        )
    return libsimba_settings.instance
