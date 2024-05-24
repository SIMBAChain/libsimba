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

import logging

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from libsimba.schemas import AuthProviderName, AuthToken, ConnectionConfig, Login


logger = logging.getLogger(__name__)


class AuthProvider(ABC):

    def provider(self) -> AuthProviderName:
        return AuthProviderName.NOOP

    @abstractmethod
    async def login(
        self,
        login: Login,
        headers: Dict[str, Any],
        config: ConnectionConfig = None,
    ) -> Optional[AuthToken]:
        """Login by adding headers and return a token"""

    @abstractmethod
    def login_sync(
        self,
        login: Login,
        headers: Dict[str, Any],
        config: ConnectionConfig = None,
    ) -> Optional[AuthToken]:
        """Login by adding headers  and return a token"""
