import logging
import os

from typing import Optional

from libsimba.schemas import AuthFlow, AuthProviderName
from pydantic import BaseSettings, validator


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
    conf = get_config_file(os.path.dirname(os.path.dirname(__file__)))
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
    AUTH_SCOPE: Optional[str]
    """ Optional scope. This is set by auth providers if not given """
    AUTH_REALM: Optional[str]
    """ Optional realm ID. Used for KeyCloak """
    WRITE_TOKEN_TO_FILE: bool = True
    """ If set to true, tokens will be cached on the file system. Otherwise they are cached in memory """
    TOKEN_DIR: str = "./"
    """ If WRITE_TOKEN_TO_FILE is true, this should be set to where tokens should be stored."""

    @validator("AUTH_FLOW")
    def set_auth_flow(cls, v: str) -> str:
        return v.lower()

    @validator("API_BASE_URL")
    def set_api_url(cls, v: str) -> str:
        if v.endswith("/"):
            v = v[:-1]
        return v

    @validator("AUTH_BASE_URL")
    def set_auth_url(cls, v: str) -> str:
        if v.endswith("/"):
            v = v[:-1]
        return v

    class Config:
        env_prefix = "SIMBA_"
        env_file = locate_config()


settings = Settings()

if __name__ == "__main__":
    print(locate_config())
