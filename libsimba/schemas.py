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

import mimetypes

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import IO, Any, AnyStr, Dict, List, Optional, Tuple, Type, Union

from pydantic import BaseModel, FieldValidationInfo, field_validator, model_validator

import httpx


class AuthFlow(str, Enum):
    CLIENT_CREDENTIALS = "client_credentials"
    API_KEY = "api-key"


class AuthProviderName(str, Enum):
    BLK = "BLK"
    KC = "KC"
    NOOP = "NOOP"
    PLAT = "PLAT"


class AuthToken(BaseModel):
    token: str
    type: Optional[str] = None
    expires: datetime

    @field_validator("expires")
    def do_datetime(cls, v: Union[datetime, str]):
        if isinstance(v, str):
            v = datetime.fromisoformat(v)
        return v.replace(tzinfo=timezone.utc)


class ConnectionConfig(BaseModel):
    timeout: float = 5.0
    connection_retries: int = 1
    max_attempts: int = 3
    http2: bool = False
    # a path to a cert file or false to turn off verification
    verify: Optional[Union[bool, str]] = None
    
    close_connection_after_use: bool = True
    
    httpx_class: Optional[Type[httpx.Client]] = httpx.Client
    httpx_extra_kwargs: Optional[Dict[str, Any]] = {}
    async_httpx_class: Optional[Type[httpx.AsyncClient]] = httpx.AsyncClient
    async_httpx_extra_kwargs: Optional[Dict[str, Any]] = {}


class Login(BaseModel):
    auth_flow: AuthFlow
    client_id: str
    client_secret: Optional[str] = None
    provider: Optional[AuthProviderName] = None

    @field_validator("client_secret")
    def set_secret(cls, v: Optional[str], info: FieldValidationInfo) -> str:
        values = info.data
        if not v and values.get("auth_flow") in [
            AuthFlow.CLIENT_CREDENTIALS,
            AuthFlow.API_KEY,
        ]:
            raise ValueError(
                "Client Secret is required if auth flow is client-credentials or api key"
            )
        return v


class FilterOp(str, Enum):
    EQ = "equals"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    CONTAINS = "contains"
    STARTSWITH = "startswith"
    EXACT = "exact"
    IEXACT = "iexact"
    ICONTAINS = "icontains"
    ISTARTSWITH = "istartswith"
    IS = "is"
    IN = "in"


class FieldFilter(BaseModel):
    op: FilterOp
    field: str
    value: Any


class MethodCallArgs(BaseModel):
    args: Optional[dict] = {}


class SearchFilter(BaseModel):
    filters: List[FieldFilter] = []
    fields: Optional[List[str]] = None
    limit: Optional[int] = None
    offset: Optional[int] = None
    page: Optional[int] = None
    size: Optional[int] = None

    def has_filter(self, field: str):
        for filter in self.filters:
            if filter.field == field:
                return True
        return False

    def has_filter_value(self, field: str, op: FilterOp, value: Any):
        for filter in self.filters:
            if filter.field == field and filter.op == op and filter.value == value:
                return True
        return False

    def add_filter(self, field_filter: FieldFilter):
        self.filters.append(field_filter)

    @property
    def filter_query(self) -> dict:
        q = {}
        for filter in self.filters:
            v = filter.value
            if isinstance(filter.value, (list, tuple)):
                v = [str(val) for val in filter.value]
                v = ",".join(v)
            if filter.op in [FilterOp.EXACT, FilterOp.EQ]:
                q["filter[{}]".format(filter.field)] = v
            else:
                q["filter[{}.{}]".format(filter.field, filter.op.value)] = v
        if self.fields:
            q["fields"] = ",".join(self.fields)
        if self.limit:
            q["limit"] = self.limit
        if self.offset:
            q["offset"] = self.offset
        if self.page:
            q["page"] = self.page
        if self.size:
            q["size"] = self.size
        return q

    @property
    def query(self) -> dict:
        q = {}
        for filter in self.filters:
            v = filter.value
            if isinstance(filter.value, (list, tuple)):
                v = [str(val) for val in filter.value]
                v = ",".join(v)
            if filter.op in [FilterOp.EXACT, FilterOp.EQ]:
                q[filter.field] = v
            else:
                q["{}__{}".format(filter.field, filter.op.value)] = v
        if self.fields:
            q["fields"] = ",".join(self.fields)
        if self.limit:
            q["limit"] = self.limit
        if self.offset:
            q["offset"] = self.offset
        if self.page:
            q["page"] = self.page
        if self.size:
            q["size"] = self.size
        return q


class TxnHeaderName(str, Enum):
    DYNAMIC_PRICING = "txn-dynamic-pricing"
    EXTERNAL = "txn-external"
    RUN_LOCAL = "txn-force-run-local"
    DELEGATE = "txn-delegate"
    NONCE = "txn-nonce"
    SENDER_TOKEN = "txn-sender-token"
    SENDER = "txn-sender"
    VALUE = "txn-value"
    ACCOUNT = "txn-account"


class TxnHeaders(BaseModel):
    dynaminc_pricing: Optional[str] = None
    external: Optional[str] = None
    run_local: Optional[str] = None
    delegate: Optional[str] = None
    nonce: Optional[str] = None
    sender_token: Optional[str] = None
    sender: Optional[str] = None
    value: Optional[str] = None
    account: Optional[Tuple[Optional[str], str]] = None

    def as_headers(self) -> dict:
        headers = {}
        if self.dynaminc_pricing:
            headers[TxnHeaderName.DYNAMIC_PRICING.value] = self.dynaminc_pricing
        if self.external:
            headers[TxnHeaderName.EXTERNAL.value] = self.external
        if self.run_local:
            headers[TxnHeaderName.RUN_LOCAL.value] = self.run_local
        if self.delegate:
            headers[TxnHeaderName.DELEGATE.value] = self.delegate
        if self.nonce:
            headers[TxnHeaderName.NONCE.value] = self.nonce
        if self.sender_token:
            headers[TxnHeaderName.SENDER_TOKEN.value] = self.sender_token
        if self.sender:
            headers[TxnHeaderName.SENDER.value] = self.sender
        if self.value:
            headers[TxnHeaderName.VALUE.value] = self.value
        if self.account:
            if self.account[0] is not None:
                headers[TxnHeaderName.ACCOUNT.value] = (
                    f"{self.account[0]}:{self.account[1]}"
                )
            else:
                headers[TxnHeaderName.ACCOUNT.value] = self.account[1]
        return headers


class File(BaseModel):
    path: Optional[str] = None
    name: Optional[str] = None
    mime: Optional[str] = None
    fp: Optional[Any] = None
    close_on_complete: Optional[bool] = True

    @model_validator(mode="before")
    def set_name_and_mime(cls, data: dict) -> dict:
        name = data.get("name")
        path = data.get("path")
        mime = data.get("mime")
        if name is None:
            if path is None:
                raise ValueError("Name must be provided if path is not set")
            data["name"] = Path(data.get("path", "")).name
        if mime is None:
            mime_type, encoding = mimetypes.guess_type(data.get("name"))
            if mime_type:
                data["mime"] = mime_type
            else:
                data["mime"] = "application/octet-stream"
        return data

    def open(self) -> IO[AnyStr]:
        if not self.fp:
            self.fp = open(self.path, "rb")
        return self.fp

    def close(self) -> None:
        if self.fp and self.close_on_complete:
            self.fp.close()


class FileDict(object):
    def __init__(self, file: File = None, files: List[File] = None):
        self._file_objects: List[File] = []
        self.add(file=file, files=files)

    def add(self, file: File = None, files: List[File] = None):
        if file and file.name:
            self._file_objects.append(file)
        if files:
            for file in files:
                if file and file.name:
                    self._file_objects.append(file)

    @property
    def files(self):
        return self._file_objects

    def open(self) -> Dict[str, Tuple[str, IO[Any], str]]:
        return {f.name: (f.name, f.open(), f.mime) for f in self._file_objects}

    def close(self):
        if self._file_objects:
            for file in self._file_objects:
                file.close()
