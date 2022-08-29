import json
import logging

from typing import AsyncGenerator, Generator, List, Optional, Union

import httpx

from httpx import ConnectError, InvalidURL, ProtocolError, RequestError, Response
from libsimba.auth.client_credentials import ClientCredentials
from libsimba.config import settings
from libsimba.exceptions import (
    LibSimbaException,
    SimbaInvalidURLException,
    SimbaRequestException,
)
from libsimba.schemas import (
    ConnectionConfig,
    FileDict,
    Login,
    MethodCallArgs,
    SearchFilter,
)
from libsimba.utils import async_http_client, build_url, http_client


PROVIDERS = {"client_credentials": ClientCredentials()}

logger = logging.getLogger(__name__)


class SimbaRequest(object):
    def __init__(
        self,
        endpoint: str,
        method: str = "GET",
        query_params: Union[dict, SearchFilter] = None,
        login: Login = None,
    ):
        """
        Create a SimbaRequest

        :param endpoint: Application id or name
        :type app_id: str
        :param \**kwargs:
            See below
        :Keyword Arguments:
            * *method* (``str``) - Optional - default ``GET``
            * *query_params* (``Union of dict or SearchFilter``) - Optional
            * *login* (``Login``) - Optional
        :return: a request object
        :rtype: SimbaRequest
        """
        self.endpoint = endpoint or ""
        query_params = query_params or {}
        if isinstance(query_params, SearchFilter):
            query_params = query_params.filter_query
        self.query_params = query_params
        self.curr_login = login or self.default_login
        self.method = method.upper()
        self._status = -1
        self._response = None
        self._json_response = None

    def log_me(
        self, headers: dict = None, params: dict = None, current_method: str = None
    ) -> str:
        s = f"method: {self.method}, url: {self.url}"
        if headers:
            s = f"{s}, headers: {headers}"
        if params:
            s = f"{s}, params: {params}"
        if self.status:
            s = f"{s}, status: {self.status}"
        if self.json_response:
            s = f"{s}, json_response: {self.json_response}"
        if self.response:
            s = f"{s}, response: {self.response}"
        if not current_method:
            current_method = "request"
        s = f"[SimbaRequest] :: {current_method} : {s}"
        return s

    @property
    def default_login(self) -> Login:
        """
        Get a default login based on the settings

        :return: a default login
        :rtype: Login
        """
        return Login(
            auth_flow=settings.AUTH_FLOW,
            client_id=settings.AUTH_CLIENT_ID,
            client_secret=settings.AUTH_CLIENT_SECRET,
        )

    @property
    def url(self) -> str:
        """
        Return the full request URL including base URL, path and query params

        :return: the URL
        :rtype: str
        """
        return build_url(settings.API_BASE_URL, self.endpoint, self.query_params)

    @property
    def response(self) -> httpx.Response:
        """
        The HTTPX response object from the request.

        :return: HTTPX response object
        :rtype: httpx.Response
        """
        return self._response

    @property
    def status(self) -> Optional[int]:
        """
        The HTTP status from the response. May be None.

        :return: status code
        :rtype: Optional[int]
        """
        return self._status

    @property
    def json_response(self) -> dict:
        """
        The JSON response object from the request.

        :return: JSON response object
        :rtype: dict
        """
        return self._json_response

    @staticmethod
    def login(
        login: Login, headers: Optional[dict] = None, config: ConnectionConfig = None
    ) -> dict:
        """
        Login.

        :param login: A Login object
        :type login: Login
        :param \**kwargs:
            See below
        :Keyword Arguments:
            * **config** (`Optional[ConnectionConfig]`)
        :return: HTTP Authorization header
        :rtype: dict
        """
        headers = headers or {}
        auth_token = PROVIDERS[login.auth_flow].login_sync(
            client_id=login.client_id, client_secret=login.client_secret, config=config
        )
        headers["Authorization"] = f"Bearer {auth_token.token}"
        return headers

    @staticmethod
    async def async_login(
        login: Login, headers: Optional[dict] = None, config: ConnectionConfig = None
    ) -> dict:
        """
        Async login.

        :param login: A Login object
        :type login: Login
        :param \**kwargs:
            See below
        :Keyword Arguments:
            * **config** (`Optional[ConnectionConfig]`)
        :return: HTTP Authorization header
        :rtype: dict
        """
        headers = headers or {}
        auth_token = await PROVIDERS[login.auth_flow].login(
            client_id=login.client_id, client_secret=login.client_secret, config=config
        )
        headers["Authorization"] = f"Bearer {auth_token.token}"
        return headers

    async def download(
        self,
        location: str,
        headers: Optional[dict] = None,
        config: ConnectionConfig = None,
    ) -> None:
        """
        Async download data and write it to ``location``.

        :param location: A local file system location to write to.
        :type location: str
        :param \**kwargs:
            See below
        :Keyword Arguments:
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: None
        """
        headers = SimbaRequest.login(self.curr_login, headers)
        logger.debug(self.log_me(headers=headers, current_method="download"))
        with open(location, "wb") as output:
            async with async_http_client(config=config) as async_client:
                async with async_client.stream(
                    "GET", self.url, headers=headers, follow_redirects=True
                ) as raw:
                    async for chunk in raw.aiter_raw():
                        output.write(chunk)

    def download_sync(
        self,
        location: str,
        headers: Optional[dict] = None,
        config: ConnectionConfig = None,
    ) -> None:
        """
        Download data and write it to ``location``.

        :param location: A local file system location to write to.
        :type location: str
        :param \**kwargs:
            See below
        :Keyword Arguments:
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: None
        """
        headers = SimbaRequest.login(self.curr_login, headers, config=config)
        logger.debug(self.log_me(headers=headers, current_method="download_sync"))
        with open(location, "wb") as output:
            with http_client(config=config) as client:
                with client.stream(
                    "GET", self.url, headers=headers, follow_redirects=True
                ) as raw:
                    for chunk in raw.iter_raw():
                        output.write(chunk)

    def call_sync(
        self,
        args: Optional[MethodCallArgs] = None,
        headers: Optional[dict] = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        Call a getter method in a contract.
        :param \**kwargs:
            See below
        :Keyword Arguments:
            * **args** (`Optional[MethodCallArgs]`)
            * **headers** (`Optional[dict]`)
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: return value dictionary containing, return value, request ID and status
        :rtype: dict
        """
        headers = SimbaRequest.login(self.curr_login, headers, config=config)
        params = args.args if args else None
        logger.debug(
            self.log_me(headers=headers, params=params, current_method="call_sync")
        )
        with http_client(config=config) as client:
            response = client.get(
                self.url, headers=headers, follow_redirects=True, params=params
            )
            return self._process_response(response)

    async def call(
        self,
        args: Optional[MethodCallArgs] = None,
        headers: Optional[dict] = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        Call a getter method in a contract async.
        :param \**kwargs:
            See below
        :Keyword Arguments:
            * **args** (`Optional[MethodCallArgs]`)
            * **headers** (`Optional[dict]`)
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: return value dictionary containing, return value, request ID and status
        :rtype: dict
        """
        headers = await SimbaRequest.async_login(
            self.curr_login, headers, config=config
        )
        params = args.args if args else None
        logger.debug(self.log_me(headers=headers, params=params, current_method="call"))
        async with async_http_client(config=config) as async_client:
            response = await async_client.get(
                self.url, headers=headers, follow_redirects=True, params=params
            )
            return self._process_response(response)

    def send_sync(
        self,
        headers: Optional[dict] = None,
        json_payload: Optional[dict] = None,
        files: FileDict = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        Send a request. Can be either GET, PUT or POST.
        :param \**kwargs:
            See below
        :Keyword Arguments:
            * **headers** (`Optional[dict]`) - optional headers
            * **json_payload** (`Optional[dict]`) - optional payload
            * **files** (`Optional[FileDict]`) - optional files to upload
            * **config** (`Optional[ConnectionConfig]`) - optional connection config
        :return: A dictionary response object
        :rtype: dict
        """
        headers = SimbaRequest.login(self.curr_login, headers, config=config)
        logger.debug(self.log_me(headers=headers, current_method="send_sync"))
        with http_client(config=config) as client:
            if self.method == "GET":
                response = client.get(self.url, headers=headers, follow_redirects=True)
                return self._process_response(response)
            json_payload = json_payload or {}
            if self.method == "PUT":
                response = client.put(
                    self.url,
                    headers=headers,
                    json=json_payload,
                    follow_redirects=True,
                )
            elif self.method == "POST":
                if files is not None:
                    data = {key: json.dumps(json_payload[key]) for key in json_payload}
                    response = client.post(
                        self.url,
                        headers=headers,
                        data=data,
                        files=files.open(),
                        follow_redirects=True,
                    )
                    files.close()
                else:
                    response = client.post(
                        self.url,
                        headers=headers,
                        json=json_payload,
                        follow_redirects=True,
                    )
            return self._process_response(response)

    def retrieve_iter_sync(
        self,
        headers: Optional[dict] = None,
        config: ConnectionConfig = None,
    ) -> Generator[List[dict], None, None]:
        """
        Get multiple results as a generator. This will loop through paging if the result is pageed.
        :param \**kwargs:
            See below
        :Keyword Arguments:
            * **headers** (`Optional[dict]`) - optional headers
            * **config** (`Optional[ConnectionConfig]`) - optional connection config
        :return: A generator of lists of dicts
        :rtype: Generator[List[dict], None, None]
        """
        headers = SimbaRequest.login(self.curr_login, headers, config=config)
        logger.debug(self.log_me(headers=headers, current_method="retrieve_iter_sync"))
        with http_client(config=config) as client:
            next_page_url = self.url
            while next_page_url is not None:
                r = client.get(next_page_url, headers=headers, follow_redirects=True)
                self._json_response = self._json_response_or_raise(r)
                results = self._json_response.get("results")
                if not results:
                    yield None
                    return
                next_page_url = self._json_response.get("next")
                yield results

    def retrieve_sync(
        self,
        headers: Optional[dict] = None,
        config: ConnectionConfig = None,
    ) -> List[dict]:
        """
        Get multiple results as a List. This will NOT loop through paging if the result is pageed.
        :param \**kwargs:
            See below
        :Keyword Arguments:
            * **headers** (`Optional[dict]`) - optional headers
            * **config** (`Optional[ConnectionConfig]`) - optional connection config
        :return: A list of objects
        :rtype: List[dict]
        """
        headers = SimbaRequest.login(self.curr_login, headers, config=config)
        logger.debug(self.log_me(headers=headers, current_method="retrieve_sync"))
        with http_client(config=config) as client:
            r = client.get(self.url, headers=headers, follow_redirects=True)
            self._json_response = self._json_response_or_raise(r)
            results = self.json_response.get("results")
        return results

    async def retrieve_iter(
        self,
        headers: Optional[dict] = None,
        config: ConnectionConfig = None,
    ) -> AsyncGenerator[List[dict], None]:
        """
        Get multiple results as an async generator. This will loop through paging if the result is pageed.
        :param \**kwargs:
            See below
        :Keyword Arguments:
            * **headers** (`Optional[dict]`) - optional headers
            * **config** (`Optional[ConnectionConfig]`) - optional connection config
        :return: An async generator of lists of dicts
        :rtype: AsyncGenerator[List[dict], None]
        """
        headers = await SimbaRequest.async_login(
            self.curr_login, headers, config=config
        )
        logger.debug(self.log_me(headers=headers, current_method="retrieve_iter"))
        async with async_http_client(config=config) as async_client:
            next_page_url = self.url
            while next_page_url is not None:
                r = await async_client.get(
                    next_page_url, headers=headers, follow_redirects=True
                )
                self._json_response = self._json_response_or_raise(r)
                results = self._json_response.get("results")
                if not results:
                    yield None
                    break
                next_page_url = self._json_response.get("next")
                yield results

    async def retrieve(
        self,
        headers: Optional[dict] = None,
        config: ConnectionConfig = None,
    ) -> List[dict]:
        """
        Get multiple results as a List. This will NOT loop through paging if the result is pageed.
        :param \**kwargs:
            See below
        :Keyword Arguments:
            * **headers** (`Optional[dict]`) - optional headers
            * **config** (`Optional[ConnectionConfig]`) - optional connection config
        :return: A list of objects
        :rtype: List[dict]
        """
        headers = await SimbaRequest.async_login(
            self.curr_login, headers, config=config
        )
        logger.debug(self.log_me(headers=headers, current_method="retrieve"))
        async with async_http_client(config=config) as async_client:
            r = await async_client.get(self.url, headers=headers, follow_redirects=True)
            self._json_response = self._json_response_or_raise(r)
            results = self.json_response.get("results")
        return results

    async def send(
        self,
        headers: Optional[dict] = None,
        json_payload: Optional[dict] = None,
        files: FileDict = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        Send a request. Can be either GET, PUT or POST.
        :param \**kwargs:
            See below
        :Keyword Arguments:
            * **headers** (`Optional[dict]`) - optional headers
            * **json_payload** (`Optional[dict]`) - optional payload
            * **files** (`Optional[FileDict]`) - optional files to upload
            * **config** (`Optional[ConnectionConfig]`) - optional connection config
        :return: A dictionary response object
        :rtype: dict
        """
        headers = await SimbaRequest.async_login(
            self.curr_login, headers, config=config
        )
        logger.debug(self.log_me(headers=headers, current_method="send"))
        async with async_http_client(config=config) as async_client:
            if self.method == "GET":
                response = await async_client.get(
                    self.url, headers=headers, follow_redirects=True
                )
                return self._process_response(response)
            json_payload = json_payload or {}
            if self.method == "PUT":
                response = await async_client.post(
                    self.url,
                    headers=headers,
                    json=json_payload,
                    follow_redirects=True,
                )
            elif self.method == "POST":
                if files is not None:
                    data = {key: json.dumps(json_payload[key]) for key in json_payload}
                    response = await async_client.post(
                        self.url,
                        headers=headers,
                        data=data,
                        follow_redirects=True,
                        files=files.open(),
                    )
                    files.close()
                else:
                    response = await async_client.post(
                        self.url,
                        headers=headers,
                        json=json_payload,
                        follow_redirects=True,
                    )
            return self._process_response(response)

    def _process_response(self, response: Response) -> dict:
        json_response = self._json_response_or_raise(response)
        self._json_response = json_response
        return json_response

    def _json_response_or_raise(self, response: Response) -> dict:
        try:
            self._response = response
            if self._response.status_code:
                self._status = self._response.status_code
            response.raise_for_status()
            json_response = response.json()
            logger.debug(
                self.log_me(
                    headers=response.headers, current_method="json_response_or_raise"
                )
            )
        except (InvalidURL, ConnectError, ProtocolError, ValueError) as e:
            raise SimbaInvalidURLException(str(e))
        except (RequestError) as e:
            raise SimbaRequestException(str(e))
        except Exception as e:
            raise LibSimbaException(message=str(e))
        return json_response


class GetRequest(SimbaRequest):
    def __init__(
        self,
        endpoint: str,
        query_params: Union[dict, SearchFilter] = None,
        login: Login = None,
    ):
        super().__init__(
            endpoint=endpoint, method="GET", query_params=query_params, login=login
        )

    def get_sync(
        self,
        headers: Optional[dict] = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        Send a GET request.
        :param \**kwargs:
            See below
        :Keyword Arguments:
            * **headers** (`Optional[dict]`) - optional headers
            * **config** (`Optional[ConnectionConfig]`) - optional connection config
        :return: A dictionary response object
        :rtype: dict
        """
        return self.send_sync(headers=headers, config=config)

    async def get(
        self,
        headers: Optional[dict] = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        Send a GET request.
        :param \**kwargs:
            See below
        :Keyword Arguments:
            * **headers** (`Optional[dict]`) - optional headers
            * **config** (`Optional[ConnectionConfig]`) - optional connection config
        :return: A dictionary response object
        :rtype: dict
        """
        return await self.send(headers=headers, config=config)


class PostRequest(SimbaRequest):
    def __init__(
        self,
        endpoint: str,
        login: Login = None,
    ):
        super().__init__(endpoint=endpoint, method="POST", login=login)

    def post_sync(
        self,
        headers: Optional[dict] = None,
        json_payload: Optional[dict] = None,
        files: FileDict = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        Send a POST request.
        :param \**kwargs:
            See below
        :Keyword Arguments:
            * **headers** (`Optional[dict]`) - optional headers
            * **json_payload** (`Optional[dict]`) - optional payload
            * **files** (`Optional[FileDict]`) - optional files to upload
            * **config** (`Optional[ConnectionConfig]`) - optional connection config
        :return: A dictionary response object
        :rtype: dict
        """
        return self.send_sync(
            headers=headers, json_payload=json_payload, files=files, config=config
        )

    async def post(
        self,
        headers: Optional[dict] = None,
        json_payload: Optional[dict] = None,
        files: FileDict = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        Send a POST request.
        :param \**kwargs:
            See below
        :Keyword Arguments:
            * **headers** (`Optional[dict]`) - optional headers
            * **json_payload** (`Optional[dict]`) - optional payload
            * **files** (`Optional[FileDict]`) - optional files to upload
            * **config** (`Optional[ConnectionConfig]`) - optional connection config
        :return: A dictionary response object
        :rtype: dict
        """
        return await self.send(
            headers=headers, json_payload=json_payload, files=files, config=config
        )


class PutRequest(SimbaRequest):
    def __init__(
        self,
        endpoint: str,
        login: Login = None,
    ):
        super().__init__(endpoint=endpoint, method="PUT", login=login)

    def put_sync(
        self,
        headers: Optional[dict] = None,
        json_payload: Optional[dict] = None,
        files: FileDict = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        Send a PUT request.
        :param \**kwargs:
            See below
        :Keyword Arguments:
            * **headers** (`Optional[dict]`) - optional headers
            * **json_payload** (`Optional[dict]`) - optional payload
            * **files** (`Optional[FileDict]`) - optional files to upload
            * **config** (`Optional[ConnectionConfig]`) - optional connection config
        :return: A dictionary response object
        :rtype: dict
        """
        return self.send_sync(
            headers=headers, json_payload=json_payload, files=files, config=config
        )

    async def put(
        self,
        headers: Optional[dict] = None,
        json_payload: Optional[dict] = None,
        files: FileDict = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        Send a PUT request.
        :param \**kwargs:
            See below
        :Keyword Arguments:
            * **headers** (`Optional[dict]`) - optional headers
            * **json_payload** (`Optional[dict]`) - optional payload
            * **files** (`Optional[FileDict]`) - optional files to upload
            * **config** (`Optional[ConnectionConfig]`) - optional connection config
        :return: A dictionary response object
        :rtype: dict
        """
        return await self.send(
            headers=headers, json_payload=json_payload, files=files, config=config
        )


class DeleteRequest(SimbaRequest):
    def __init__(
        self,
        endpoint: str,
        login: Login = None,
    ):
        super().__init__(endpoint=endpoint, method="DELETE", login=login)

    def delete_sync(
        self,
        headers: Optional[dict] = None,
        config: ConnectionConfig = None,
    ) -> Optional[dict]:
        """
        Send a DELETE request.
        :param \**kwargs:
            See below
        :Keyword Arguments:
            * **headers** (`Optional[dict]`) - optional headers
            * **config** (`Optional[ConnectionConfig]`) - optional connection config
        :return: A dictionary response object or None
        :rtype: Optional[dict]
        """
        return self.send_sync(headers=headers, config=config)

    async def delete(
        self,
        headers: Optional[dict] = None,
        config: ConnectionConfig = None,
    ) -> Optional[dict]:
        """
        Send a DELETE request.
        :param \**kwargs:
            See below
        :Keyword Arguments:
            * **headers** (`Optional[dict]`) - optional headers
            * **config** (`Optional[ConnectionConfig]`) - optional connection config
        :return: A dictionary response object or None
        :rtype: Optional[dict]
        """
        return await self.send(headers=headers, config=config)
