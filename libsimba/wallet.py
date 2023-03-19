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

from abc import ABC, abstractmethod


class Wallet(ABC):

    @abstractmethod
    def forget_wallet(self):
        """
        Remove the current wallet
        """

    @abstractmethod
    def wallet_available(self) -> bool:
        """
        Does a wallet currently exists?

        Returns:
            Returns a boolean indicating if a wallet exist.
        """

    @abstractmethod
    def get_address(self) -> str:
        """
        The address associated with this wallet

        Returns:
            Returns the address associated with this wallet
        """

    @abstractmethod
    def get_private_key(self) -> str:
        """
        The private key associated with this wallet

        Returns:
            Returns the private key associated with this wallet
        """

    @abstractmethod
    def sign(self, payload: dict) -> dict:
        """
        Sign a transaction payload with the wallet

        Args:
            payload: a transaction object
        Returns:
            Returns the signed transaction
        """
