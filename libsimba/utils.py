import asyncio
import json
import logging
import os
import random

from datetime import datetime
from email.utils import parsedate_to_datetime
from enum import Enum
from logging.config import dictConfig, fileConfig
from time import sleep
from typing import Dict, Iterable, Mapping, Optional, Union
from urllib.parse import urlencode, urlparse, urlunparse

import httpx

from httpx import AsyncHTTPTransport, HTTPTransport
from libsimba import schemas


log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logging.conf")

log_file = os.environ.get("SIMBA_LOG_CONFIG", log_file_path)
if log_file.endswith(".json"):
    with open(log_file) as json_conf:
        dictConfig(json.load(json_conf))
else:
    fileConfig(log_file)

log = logging.getLogger(__name__)

class Path(str, Enum):
    WHOAMI = "/user/whoami/"
    APPS = "/v2/apps/"
    APP = "/v2/apps/{}/"
    APP_TXNS = "/v2/apps/{}/transactions/"
    APP_TXN = "/v2/apps/{}/transactions/{}/"
    APP_CONTRACT = "/v2/apps/{}/contract/{}/"
    APP_CONTRACTS = "/v2/apps/{}/contracts/"
    CONTRACT_TXNS = "/v2/apps/{}/contract/{}/transactions/"
    CONTRACT_TXN = "/v2/apps/{}/contract/{}/transaction/{}/"
    CONTRACTS = "/v2/apps/{}/contracts/"
    VALIDATE_BUNDLE = "/v2/apps/{}/validate/{}/{}/"
    BUNDLE = "/v2/apps/{}/contract/{}/bundle/{}/"
    BUNDLE_FILE = "/v2/apps/{}/contract/{}/bundle/{}/filename/{}/"
    BUNDLE_MANIFEST = "/v2/apps/{}/contract/{}/bundle/{}/manifest/"
    CONTRACT_INFO = "/v2/apps/{}/contract/{}/info"
    CONTRACT_EVENTS = "/v2/apps/{}/contract/{}/events/{}/"
    CONTRACT_RECEIPT = "/v2/apps/{}/contract/{}/receipt/{}/"
    CONTRACT_METHOD = "/v2/apps/{}/contract/{}/{}/"
    SYNC_CONTRACT_METHOD = "/v2/apps/{}/sync/contract/{}/{}/"
    USER_FUND_ADDRESS = "/user/account/{}/fund/"
    USER_ADDRESS_BALANCE = "/user/account/{}/balance/{}/"
    ADMIN_WALLET_SET = "/admin/users/{}/wallet/set/"
    USER_WALLET_SET = "/user/wallet/set/"
    USER_WALLET = "/user/wallet/"
    ORGANISATION = "/v2/organisations/{}/"
    ORGANISATIONS = "/v2/organisations/"
    ORG_APP = "/v2/organisations/{}/applications/{}/"
    ORG_APPS = "/v2/organisations/{}/applications/"
    ORG_TXN = "/v2/organisations/{}/transactions/{}/"
    ORG_TXNS = "/v2/organisations/{}/transactions/"
    DESIGNS = "/v2/organisations/{}/contract_designs/"
    DESIGN = "/v2/organisations/{}/contract_designs/{}/"
    CONTRACT_ARTIFACTS = "/v2/organisations/{}/contract_artifacts/"
    CONTRACT_ARTIFACT = "/v2/organisations/{}/contract_artifacts/{}/"
    DEPLOYED_CONTRACTS = "/v2/organisations/{}/deployed_contracts/"
    DEPLOYED_CONTRACT = "/v2/organisations/{}/deployed_contracts/{}/"
    DESIGN_DEPLOY = "/v2/organisations/{}/contract_designs/{}/deploy/"
    DEPLOYMENT = "/v2/organisations/{}/deployments/{}/"
    DEPLOYMENTS = "/v2/organisations/{}/deployments/"
    STORAGES = "/v2/organisations/{}/storage/"
    BLOCKCHAINS = "/v2/organisations/{}/blockchains/"
    SUBSCRIPTIONS = "/v2/organisations/{}/subscriptions/"
    SUBSCRIPTION = "/v2/organisations/{}/subscriptions/{}/"
    NOTIFICATION_CONFIGS = "/v2/organisations/{}/notification_config/"


class RetryTransport(httpx.AsyncBaseTransport, httpx.BaseTransport):

    RETRYABLE_METHODS = frozenset(["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"])
    RETRYABLE_STATUS_CODES = frozenset([413, 429, 500, 502, 503, 504])

    MAX_BACKOFF_WAIT = 10

    def __init__(
        self,
        wrapped_transport: Union[httpx.BaseTransport, httpx.AsyncBaseTransport],
        max_attempts: int = 3,
        max_backoff_wait: float = MAX_BACKOFF_WAIT,
        backoff_factor: float = 0.5,
        jitter_ratio: float = 0.1,
        respect_retry_after_header: bool = True,
        retryable_methods: Iterable[str] = None,
        retry_status_codes: Iterable[int] = None,
    ) -> None:
        self.wrapped_transport = wrapped_transport
        if jitter_ratio < 0 or jitter_ratio > 0.5:
            raise ValueError(
                f"jitter ratio should be between 0 and 0.5, actual {jitter_ratio}"
            )

        self.max_attempts = max_attempts
        self.backoff_factor = backoff_factor
        self.respect_retry_after_header = respect_retry_after_header
        self.retryable_methods = (
            frozenset(retryable_methods)
            if retryable_methods
            else self.RETRYABLE_METHODS
        )
        self.retry_status_codes = (
            frozenset(retry_status_codes)
            if retry_status_codes
            else self.RETRYABLE_STATUS_CODES
        )
        self.jitter_ratio = jitter_ratio
        self.max_backoff_wait = max_backoff_wait
        self.last_retry_info: Dict[int, dict] = {}

    def _calculate_sleep(
        self, attempts_made: int, headers: Union[httpx.Headers, Mapping[str, str]]
    ) -> float:
        retry_after_header = (headers.get("Retry-After") or "").strip()
        if self.respect_retry_after_header and retry_after_header:
            if retry_after_header.isdigit():
                return float(retry_after_header)

            try:
                parsed_date = parsedate_to_datetime(
                    retry_after_header
                ).astimezone()  # converts to local time
                diff = (parsed_date - datetime.now().astimezone()).total_seconds()
                if diff > 0:
                    return min(diff, self.max_backoff_wait)
            except ValueError:
                pass

        backoff = self.backoff_factor * (2 ** (attempts_made - 1))
        jitter = (backoff * self.jitter_ratio) * random.choice([1, -1])  # noqa S311
        total_backoff = backoff + jitter
        return min(total_backoff, self.max_backoff_wait)

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        """
        Send a single HTTP request and return a response.

        :param request: a `Request` instance
        :type request: httpx.Request
        :return: a response
        :rtype:  httpx.Response

        Developers shouldn't typically ever need to call into this API directly,
        since the Client class provides all the higher level user-facing API
        niceties.

        In order to properly release any network resources, the response
        stream should *either* be consumed immediately, with a call to
        `response.stream.read()`, or else the `handle_request` call should
        be followed with a try/finally block to ensuring the stream is
        always closed.
        """
        self.last_retry_info = {}
        response = self.wrapped_transport.handle_request(request)
        remaining_attempts = self.max_attempts
        attempts_made = 0
        while (
            remaining_attempts > 0 and response.status_code in self.retry_status_codes
        ):
            response.close()
            sleep_time = self._calculate_sleep(attempts_made, response.headers)
            sleep(sleep_time)
            response = self.wrapped_transport.handle_request(request)
            attempts_made += 1
            remaining_attempts -= 1
            self.last_retry_info[attempts_made] = {
                "attempts_made": attempts_made,
                "max_attempts": self.max_attempts,
                "remaining_attempts": remaining_attempts,
                "sleep_time": sleep_time,
                "response_code": response.status_code,
            }
        return response

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.last_retry_info = {}
        response = await self.wrapped_transport.handle_async_request(request)
        remaining_attempts = self.max_attempts
        attempts_made = 0
        while (
            remaining_attempts > 0 and response.status_code in self.retry_status_codes
        ):
            await response.aclose()
            sleep_time = self._calculate_sleep(attempts_made, response.headers)
            await asyncio.sleep(sleep_time)
            response = await self.wrapped_transport.handle_async_request(request)
            attempts_made += 1
            remaining_attempts -= 1
            self.last_retry_info[attempts_made] = {
                "attempts_made": attempts_made,
                "max_attempts": self.max_attempts,
                "remaining_attempts": remaining_attempts,
                "sleep_time": sleep_time,
                "response_code": response.status_code,
            }
        return response

def async_http_client(config: schemas.ConnectionConfig = None) -> httpx.AsyncClient:
    """
    Create an async HTTPX client
    :param config: a connection config
    :type config: schemas.ConnectionConfig
    :return: a client
    :rtype: httpx.AsyncClient
    """
    if not config:
        config = schemas.ConnectionConfig()
    transport = RetryTransport(
        AsyncHTTPTransport(retries=config.connection_retries),
        max_attempts=config.max_attempts,
    )
    return httpx.AsyncClient(
        timeout=config.timeout, transport=transport, http2=config.http2
    )


def http_client(config: schemas.ConnectionConfig = None) -> httpx.Client:
    """
    Create an HTTPX client
    :param config: a connection config
    :type config: schemas.ConnectionConfig
    :return: a client
    :rtype: httpx.Client
    """
    if not config:
        config = schemas.ConnectionConfig()
    transport = RetryTransport(
        HTTPTransport(retries=config.connection_retries),
        max_attempts=config.max_attempts,
    )
    return httpx.Client(timeout=config.timeout, transport=transport, http2=config.http2)


def build_url(base_api_url: str, path: str, query_dict: Optional[dict]):
    query_dict = query_dict or {}
    url_parts = list(urlparse(base_api_url))
    url_parts[2] = path
    url_parts[4] = urlencode(query_dict)
    return urlunparse(url_parts)

def get_address(deployment: dict) -> Optional[str]:
    """
    Extract the primary address from a deployment object.

    :param deployment: The deployment object
    :type deployment: dict
    :return: Optional[str]
    """
    return deployment.get("primary", {}).get("address", None)

def get_deployed_artifact_id(deployment: dict) -> Optional[str]:
    """
    Extract the primary deployed artifact ID from a deployment object.

    :param deployment: The deployment object
    :type deployment: dict
    :return: Optional[str]
    """
    return deployment.get("primary", {}).get("deployed_artifact_id", None)