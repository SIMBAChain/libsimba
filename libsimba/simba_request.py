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

from typing import Any, AsyncGenerator, Dict, Generator, List, Optional, Tuple, Union

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


class Pager:

    def list(self, page: Dict[str, Any]) -> List[Any]:
        if page.get("results"):
            return page["results"]
        elif page.get("items"):
            return page["items"]
        return []

    def next(
        self, url: str, page: Dict[str, Any], params: Dict[str, Any]
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        if page.get("results"):
            return page.get("next"), None
        elif page.get("items"):
            curr_page = int(page.get("page", "1"))
            total_pages = int(page.get("pages", "1"))
            if curr_page < total_pages:
                params["page"] = curr_page + 1
                params["size"] = int(page.get("size", "50"))
                return url, params
        return None, None


class SimbaRequest(object):
    def __init__(
        self,
        endpoint: str,
        method: str = "GET",
        query_params: Union[dict, SearchFilter] = None,
        login: Login = None,
        base_url: Optional[str] = None,
        authenticated: bool = True,
    ):
        """
        Create a SimbaRequest

        :param endpoint: Application id or name
        :type app_id: str

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
        self.base_url = base_url
        self.authenticated = authenticated
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

        :return: a default log in
        :rtype: Login
        """
        return Login(
            auth_flow=settings().AUTH_FLOW,
            client_id=settings().AUTH_CLIENT_ID,
            client_secret=settings().AUTH_CLIENT_SECRET,
            provider=settings().AUTH_PROVIDER,
        )

    @property
    def url(self) -> str:
        """
        Return the full request URL including base URL, path and query params

        :return: the URL
        :rtype: str
        """
        if self.base_url:
            return build_url(self.base_url, self.endpoint, self.query_params)
        else:
            return build_url(settings().API_BASE_URL, self.endpoint, self.query_params)

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
        login: Login,
        headers: Optional[dict] = None,
        config: ConnectionConfig = None,
        authenticated: bool = True,
    ) -> dict:
        """
        Login. If an Authorization header is found in the headers,
        this is used rather than performing a login.

        :param login: A Login object
        :type login: Login

        :Keyword Arguments:
            * **headers** (`Optional[dict]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: HTTP Authorization header
        :rtype: dict
        """
        headers = headers or {}
        if not authenticated:
            return headers
        _ = PROVIDERS[login.auth_flow].login_sync(
            login=login,
            headers=headers,
            config=config,
        )
        return headers

    @staticmethod
    async def async_login(
        login: Login,
        headers: Optional[dict] = None,
        config: ConnectionConfig = None,
        authenticated: bool = True,
    ) -> dict:
        """
        Async login. If an Authorization header is found in the headers,
        this is used rather than performing a login

        :param login: A Login object
        :type login: Login


        :Keyword Arguments:
            * **headers** (`Optional[dict]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: HTTP Authorization header
        :rtype: dict
        """
        headers = headers or {}
        if not authenticated:
            return headers
        _ = await PROVIDERS[login.auth_flow].login(
            login=login,
            headers=headers,
            config=config,
        )
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

        :Keyword Arguments:
            * **headers** (`Optional[dict]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: None
        """
        headers = await SimbaRequest.async_login(
            self.curr_login, headers, config, self.authenticated
        )
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

        :Keyword Arguments:
            * **headers** (`Optional[dict]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: None
        """
        headers = SimbaRequest.login(
            self.curr_login, headers, config=config, authenticated=self.authenticated
        )
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

        :Keyword Arguments:
            * **args** (`Optional[MethodCallArgs]`)
            * **headers** (`Optional[dict]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: return value dictionary containing, return value, request ID and status
        :rtype: dict
        """
        headers = SimbaRequest.login(
            self.curr_login, headers, config=config, authenticated=self.authenticated
        )
        params = None
        if args and args.args:
            params = {}
            for k, p in args.args.items():
                if isinstance(p, (dict, list)):
                    params[k] = json.dumps(p, separators=(",", ":"))
                else:
                    params[k] = p
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

        :Keyword Arguments:
            * **args** (`Optional[MethodCallArgs]`)
            * **headers** (`Optional[dict]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: return value dictionary containing, return value, request ID and status
        :rtype: dict
        """
        headers = await SimbaRequest.async_login(
            self.curr_login, headers, config=config, authenticated=self.authenticated
        )
        params = None
        if args and args.args:
            params = {}
            for k, p in args.args.items():
                if isinstance(p, (dict, list)):
                    params[k] = json.dumps(p, separators=(",", ":"))
                else:
                    params[k] = p
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

        :Keyword Arguments:
            * **headers** (`Optional[dict]`) - optional headers
            * **json_payload** (`Optional[dict]`) - optional payload
            * **files** (`Optional[FileDict]`) - optional files to upload
            * **config** (`Optional[ConnectionConfig]`) - optional connection config
        :return: A dictionary response object
        :rtype: dict
        """
        headers = SimbaRequest.login(
            self.curr_login, headers, config=config, authenticated=self.authenticated
        )
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
            elif self.method == "PATCH":
                response = client.patch(
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
        Get multiple results as a generator. This will loop through paging if the result is paged.

        :Keyword Arguments:
            * **headers** (`Optional[dict]`) - optional headers
            * **config** (`Optional[ConnectionConfig]`) - optional connection config
        :return: A generator of lists of dicts
        :rtype: Generator[List[dict], None, None]
        """
        headers = SimbaRequest.login(
            self.curr_login, headers, config=config, authenticated=self.authenticated
        )
        logger.debug(self.log_me(headers=headers, current_method="retrieve_iter_sync"))
        with http_client(config=config) as client:
            pager = Pager()
            next_page_url = self.url
            params = self.query_params
            while next_page_url is not None:
                r = client.get(
                    next_page_url, headers=headers, follow_redirects=True, params=params
                )
                self._json_response = self._json_response_or_raise(r)
                results = pager.list(self._json_response)
                if not results:
                    yield None
                    return
                next_page_url, params = pager.next(
                    url=next_page_url, page=self._json_response, params=params
                )
                yield results

    def retrieve_sync(
        self,
        headers: Optional[dict] = None,
        config: ConnectionConfig = None,
    ) -> List[dict]:
        """
        Get multiple results as a List. This will NOT loop through paging if the result is pageed.

        :Keyword Arguments:
            * **headers** (`Optional[dict]`) - optional headers
            * **config** (`Optional[ConnectionConfig]`) - optional connection config
        :return: A list of objects
        :rtype: List[dict]
        """
        headers = SimbaRequest.login(
            self.curr_login, headers, config=config, authenticated=self.authenticated
        )
        logger.debug(self.log_me(headers=headers, current_method="retrieve_sync"))
        with http_client(config=config) as client:
            pager = Pager()
            r = client.get(self.url, headers=headers, follow_redirects=True)
            self._json_response = self._json_response_or_raise(r)
            results = pager.list(self.json_response)
        return results

    async def retrieve_iter(
        self,
        headers: Optional[dict] = None,
        config: ConnectionConfig = None,
    ) -> AsyncGenerator[List[dict], None]:
        """
        Get multiple results as an async generator. This will loop through paging if the result is pageed.

        :Keyword Arguments:
            * **headers** (`Optional[dict]`) - optional headers
            * **config** (`Optional[ConnectionConfig]`) - optional connection config
        :return: An async generator of lists of dicts
        :rtype: AsyncGenerator[List[dict], None]
        """
        headers = await SimbaRequest.async_login(
            self.curr_login, headers, config=config, authenticated=self.authenticated
        )
        logger.debug(self.log_me(headers=headers, current_method="retrieve_iter"))
        async with async_http_client(config=config) as async_client:
            pager = Pager()
            next_page_url = self.url
            params = self.query_params
            while next_page_url is not None:
                r = await async_client.get(
                    next_page_url, headers=headers, follow_redirects=True, params=params
                )
                self._json_response = self._json_response_or_raise(r)
                results = pager.list(self._json_response)
                if not results:
                    yield None
                    break
                next_page_url, params = pager.next(
                    url=next_page_url, page=self._json_response, params=params
                )
                yield results

    async def retrieve(
        self,
        headers: Optional[dict] = None,
        config: ConnectionConfig = None,
    ) -> List[dict]:
        """
        Get multiple results as a List. This will NOT loop through paging if the result is pageed.

        :Keyword Arguments:
            * **headers** (`Optional[dict]`) - optional headers
            * **config** (`Optional[ConnectionConfig]`) - optional connection config
        :return: A list of objects
        :rtype: List[dict]
        """
        headers = await SimbaRequest.async_login(
            self.curr_login, headers, config=config, authenticated=self.authenticated
        )
        logger.debug(self.log_me(headers=headers, current_method="retrieve"))
        async with async_http_client(config=config) as async_client:
            pager = Pager()
            r = await async_client.get(self.url, headers=headers, follow_redirects=True)
            self._json_response = self._json_response_or_raise(r)
            results = pager.list(self.json_response)
        return results

    async def send(
        self,
        headers: Optional[dict] = None,
        json_payload: Optional[dict] = None,
        files: Optional[FileDict] = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        Send a request. Can be either GET, PUT or POST.

        :Keyword Arguments:
            * **headers** (`Optional[dict]`) - optional headers
            * **json_payload** (`Optional[dict]`) - optional payload
            * **files** (`Optional[FileDict]`) - optional files to upload
            * **config** (`Optional[ConnectionConfig]`) - optional connection config
        :return: A dictionary response object
        :rtype: dict
        """
        headers = await SimbaRequest.async_login(
            self.curr_login, headers, config=config, authenticated=self.authenticated
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
                response = await async_client.put(
                    self.url,
                    headers=headers,
                    json=json_payload,
                    follow_redirects=True,
                )
            elif self.method == "PATCH":
                response = await async_client.patch(
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
            elif self.method == "DELETE":
                response = await async_client.delete(
                    self.url,
                    headers=headers,
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

            # response.json does not properly handle DELETE, when response.content is not present
            if not response.content:
                response._content = b'{}'

            json_response = response.json()
            logger.info(
                self.log_me(
                    headers=response.headers, current_method="json_response_or_raise"
                )
            )
            response.raise_for_status()
        except (InvalidURL, ConnectError, ProtocolError, ValueError) as e:
            raise SimbaInvalidURLException(str(e))
        except RequestError as e:
            raise SimbaRequestException(f"{e} :: {self._response.text}")
        except Exception as e:
            raise LibSimbaException(message=f"{e} :: {self._response.text}")
        return json_response


class GetRequest(SimbaRequest):
    def __init__(
        self,
        endpoint: str,
        query_params: Union[dict, SearchFilter] = None,
        login: Login = None,
        base_url: Optional[str] = None,
        authenticated: bool = True,
    ):
        super().__init__(
            endpoint=endpoint,
            method="GET",
            query_params=query_params,
            login=login,
            base_url=base_url,
            authenticated=authenticated,
        )

    def get_sync(
        self,
        headers: Optional[dict] = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        Send a GET request.

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
        base_url: Optional[str] = None,
        authenticated: bool = True,
    ):
        super().__init__(
            endpoint=endpoint,
            method="POST",
            login=login,
            base_url=base_url,
            authenticated=authenticated,
        )

    def post_sync(
        self,
        headers: Optional[dict] = None,
        json_payload: Optional[dict] = None,
        files: FileDict = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        Send a POST request.

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
        base_url: Optional[str] = None,
        authenticated: bool = True,
    ):
        super().__init__(
            endpoint=endpoint,
            method="PUT",
            login=login,
            base_url=base_url,
            authenticated=authenticated,
        )

    def put_sync(
        self,
        headers: Optional[dict] = None,
        json_payload: Optional[dict] = None,
        files: FileDict = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        Send a PUT request.

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


class PatchRequest(SimbaRequest):
    def __init__(
        self,
        endpoint: str,
        login: Login = None,
        base_url: Optional[str] = None,
        authenticated: bool = True,
    ):
        super().__init__(
            endpoint=endpoint,
            method="PATCH",
            login=login,
            base_url=base_url,
            authenticated=authenticated,
        )

    def patch_sync(
        self,
        headers: Optional[dict] = None,
        json_payload: Optional[dict] = None,
        files: FileDict = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        Send a PATCH request.

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

    async def patch(
        self,
        headers: Optional[dict] = None,
        json_payload: Optional[dict] = None,
        files: FileDict = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        Send a PATCH request.

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
        base_url: Optional[str] = None,
        authenticated: bool = True,
    ):
        super().__init__(
            endpoint=endpoint,
            method="DELETE",
            login=login,
            base_url=base_url,
            authenticated=authenticated,
        )

    def delete_sync(
        self,
        headers: Optional[dict] = None,
        config: ConnectionConfig = None,
    ) -> Optional[dict]:
        """
        Send a DELETE request.

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

        :Keyword Arguments:
            * **headers** (`Optional[dict]`) - optional headers
            * **config** (`Optional[ConnectionConfig]`) - optional connection config
        :return: A dictionary response object or None
        :rtype: Optional[dict]
        """
        return await self.send(headers=headers, config=config)
