import mimetypes

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import IO, Any, AnyStr, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, validator


class AuthFlow(str, Enum):
    CLIENT_CREDENTIALS = "client_credentials"


class AuthProviderName(str, Enum):
    BLK = "BLK"
    KC = "KC"
    NOOP = "NOOP"


class AuthToken(BaseModel):
    token: str
    type: str
    expires: datetime

    @validator("expires")
    def do_datetime(cls, v: Union[datetime, str]):
        if isinstance(v, str):
            return datetime.fromisoformat(v)
        return v


class ConnectionConfig(BaseModel):
    timeout: float = 5.0
    connection_retries: int = 1
    max_attempts: int = 3
    http2: bool = False


class Login(BaseModel):
    auth_flow: AuthFlow
    client_id: str
    client_secret: Optional[str]

    @validator("client_secret")
    def set_secret(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        if not v and values.get("auth_flow") == AuthFlow.CLIENT_CREDENTIALS:
            raise ValueError(
                "Client Secret is required if auth flow is client-credentials"
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
    fields: Optional[List[str]]
    limit: Optional[int]
    offset: Optional[int]

    def has_filter(self, field: str):
        for filter in self.filters:
            if filter.field == field:
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
                q["filter[{}.{}]".format(filter.field, filter.op)] = v
        if self.fields:
            q["fields"] = ",".join(self.fields)
        if self.limit:
            q["limit"] = self.limit
        if self.offset:
            q["offset"] = self.offset
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


class TxnHeaders(BaseModel):
    dynaminc_pricing: Optional[str]
    external: Optional[str]
    run_local: Optional[str]
    delegate: Optional[str]
    nonce: Optional[str]
    sender_token: Optional[str]
    sender: Optional[str]
    value: Optional[str]

    def as_headers(self) -> dict:
        headers = {}
        if self.dynaminc_pricing:
            headers[TxnHeaderName.DYNAMIC_PRICING] = self.dynaminc_pricing
        if self.external:
            headers[TxnHeaderName.EXTERNAL] = self.external
        if self.run_local:
            headers[TxnHeaderName.RUN_LOCAL] = self.run_local
        if self.delegate:
            headers[TxnHeaderName.DELEGATE] = self.delegate
        if self.nonce:
            headers[TxnHeaderName.NONCE] = self.nonce
        if self.sender_token:
            headers[TxnHeaderName.SENDER_TOKEN] = self.sender_token
        if self.sender:
            headers[TxnHeaderName.SENDER] = self.sender
        if self.value:
            headers[TxnHeaderName.VALUE] = self.value
        return headers


class File(BaseModel):
    path: Optional[str]
    name: Optional[str]
    mime: Optional[str]
    fp: Optional[Any]
    close_on_complete: Optional[bool] = True

    @validator("name", always=True)
    def set_name(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        if not v:
            if not values.get("path"):
                raise ValueError("Name must be provided if path is not set")
            return Path(values.get("path", "")).name
        return v

    @validator("mime", always=True)
    def set_mime(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        if not v:
            mime_type, encoding = mimetypes.guess_type(values.get("name"))
            if mime_type:
                v = mime_type
            else:
                v = "application/octet-stream"
        return v

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
