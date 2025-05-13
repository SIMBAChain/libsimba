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

import base64
import logging
import time

from typing import Any, Generator, List, Optional, Tuple, Union

from libsimba.config import settings
from libsimba.schemas import (
    ConnectionConfig,
    FieldFilter,
    FileDict,
    FilterOp,
    Login,
    MethodCallArgs,
    SearchFilter,
    TxnHeaders,
)
from libsimba.simba_contract_sync import SimbaContractSync
from libsimba.simba_request import (
    GetRequest,
    PatchRequest,
    PostRequest,
    PutRequest,
    SimbaRequest,
)
from libsimba.utils import (
    Path,
    get_address,
    get_address_by_name,
    get_deployed_artifact_id,
)


logger = logging.getLogger(__name__)


class SimbaSync:
    def __init__(self, **kwargs):
        """
        See libsimba Settings for args that can be passed.

        :Keyword Arguments:
            * args that can configure Settings if settings
            have not been initialized
        """
        settings(**kwargs)

    def smart_contract_client(
        self, app_name: str, contract_name: str
    ) -> SimbaContractSync:
        return SimbaContractSync(self, app_name, contract_name)

    def whoami(self, login: Login = None, config: ConnectionConfig = None) -> dict:
        """
        GET ``/user/whoami/``

        Get the current user.

        :Keyword Arguments:
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: user information
        :rtype: dict
        """

        return GetRequest(endpoint=Path.WHOAMI, login=login).get_sync(config=config)

    def fund(
        self,
        blockchain: str,
        address: str,
        amount: Union[str, int],
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        POST ``/user/account/{blockchain}/fund/``

        Fund an account.

        :param blockchain: The blockchain to target
        :type blockchain: str
        :param address: The address to fund
        :type address: str
        :param amount: The amount of native currency (wei) to fund. Can de a decimal int or a hex string
        :type amount: Union[str, int]

        :Keyword Arguments:
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: fund response
        :rtype: dict
        """
        inputs = {"address": address, "amount": amount}
        return PostRequest(
            endpoint=Path.USER_FUND_ADDRESS.format(blockchain),
            login=login,
        ).post_sync(config=config, json_payload=inputs)

    def balance(
        self,
        blockchain: str,
        address: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> Union[str, int]:
        """
        GET ``/user/account/{blockchain}/balance/{address}/``

        Get the balance of an account on a specific blockchain.

        :param blockchain: The blockchain to target
        :type blockchain: str
        :param address: The address to get the balance of
        :type address: str

        :Keyword Arguments:
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: the balance
        :rtype: dict
        """
        resp = GetRequest(
            endpoint=Path.USER_ADDRESS_BALANCE.format(blockchain, address), login=login
        ).get_sync(config=config)
        return resp.get("balance")

    def admin_set_wallet(
        self,
        user_id: Union[str, int],
        blockchain: str,
        pub: str,
        priv: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        POST ``/admin/users/{user}/wallet/set/``

        Admin function to set a user's wallet.
        NOTE: This is an admin function.

        :param user_id: the user ID
        :type user_id: Union[str, int]
        :param blockchain: The blockchain the wallet is intended for
        :type blockchain: str
        :param pub: The blockchain address
        :type pub: str
        :param priv: The private key
        :type priv: str

        :Keyword Arguments:
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: the wallet
        :rtype: dict
        """
        inputs = {"blockchain": blockchain, "identities": [{"pub": pub, "priv": priv}]}
        resp = PostRequest(
            endpoint=Path.ADMIN_WALLET_SET.format(user_id), login=login
        ).post_sync(config=config, json_payload=inputs)
        return resp

    def set_wallet(
        self,
        blockchain: str,
        pub: str,
        priv: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        POST ``/user/wallet/set/``

        Set current user's wallet

        :param blockchain: The blockchain the wallet is intended for
        :type blockchain: str
        :param pub: The blockchain address
        :type pub: str
        :param priv: The private key
        :type priv: str

        :Keyword Arguments:
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: the wallet
        :rtype: dict
        """
        inputs = {"blockchain": blockchain, "identities": [{"pub": pub, "priv": priv}]}
        resp = PostRequest(endpoint=Path.USER_WALLET_SET, login=login).post_sync(
            config=config, json_payload=inputs
        )
        return resp

    def get_wallet(self, login: Login = None, config: ConnectionConfig = None) -> dict:
        """
        GET ``/user/wallet/``

        Get current user's wallet

        :Keyword Arguments:
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: the wallet
        :rtype: dict
        """
        return GetRequest(endpoint=Path.USER_WALLET, login=login).get_sync(
            config=config
        )

    def parse_wallet(
        self, wallet: dict, blockchain_type: str, blockchain: str
    ) -> Optional[str]:
        """
        Extract address from a wallet structure for a given blockchain.
        The wallet structure is the JSON returned from a call to get_wallet.

        :param wallet: The wallet structure
        :type wallet: dict
        :param blockchain_type: The type of blockchain, e.g., ethereum
        :type blockchain_type: str
        :param blockchain: The blockchain network name
        :type blockchain: str
        :return: the address
        :rtype: Optional[str]
        """
        bc = (
            wallet.get("wallet", {})
            .get("identities", {})
            .get(blockchain_type, {})
            .get(blockchain, {})
        )
        for key, val in bc.items():
            if len(val) > 0:
                node = val[0]
                addr = node.get("pub")
                if addr:
                    return addr
        return None

    def create_org(
        self,
        name: str,
        display: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        POST ``/v2/organisations/``

        Create an Org. This will first search for an org with the given name and return that if found.
        Otherwise it will attempt to create one.
        NOTE: Creating orgs is typically an admin function.

        :param name: The org name
        :type name: str
        :param display: The org display name
        :type display: str

        :Keyword Arguments:
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: the org
        :rtype: dict
        """
        req = GetRequest(endpoint=Path.ORGANISATION.format(name), login=login)
        try:
            return req.get_sync(config=config)
        except Exception as ex:
            if req.status == 404:
                inputs = {"name": name, "display_name": display}
                return PostRequest(endpoint=Path.ORGANISATIONS, login=login).post_sync(
                    config=config, json_payload=inputs
                )
            else:
                raise ex

    def create_app(
        self,
        org: str,
        name: str,
        display: str,
        force: bool = False,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        POST ``/v2/organisations/{org}/applications/``

        Create an Application.
        If ``force`` is false, this will first search for an app with the given name and return that if found.
        Otherwise it will attempt to create one.

        :param org: The org name
        :type org: str
        :param name: The app name
        :type name: str
        :param display: The app display name
        :type display: str
        :param force: Whether to attempt to create before checking for existence or not. Default is true
        :type force: bool

        :Keyword Arguments:
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: the app
        :rtype: dict
        """
        if force:
            inputs = {"name": name, "display_name": display}
            return PostRequest(endpoint=Path.ORG_APPS, login=login).post_sync(
                config=config, json_payload=inputs
            )
        req = GetRequest(endpoint=Path.ORG_APP.format(org, name), login=login)
        try:
            return req.get_sync(config=config)
        except Exception as ex:
            if req.status == 404:
                inputs = {"name": name, "display_name": display}
                return PostRequest(
                    endpoint=Path.ORG_APPS.format(org), login=login
                ).post_sync(config=config, json_payload=inputs)
            else:
                raise ex

    # -------------------------------------------------
    # All proceeding functions are general App getters
    # -------------------------------------------------
    """
    GET
    /v2/apps/
    list Application
    """

    def list_applications(
        self,
        query_args: Optional[SearchFilter] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> Generator[List[dict], None, None]:
        """
        GET ``/v2/apps/``

        List applications

        :param app_id: Application id or name
        :type app_id: str

        :Keyword Arguments:
            * **query_args** (`Optional[SearchFilter]`)
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: Generator of application information
        :rtype: Generator[List[dict], None, None]
        """
        return SimbaRequest(
            endpoint=Path.APPS, query_params=query_args, login=login
        ).retrieve_iter_sync(config=config)

    def get_applications(
        self,
        query_args: Optional[SearchFilter] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> List[dict]:
        """
        GET ``/v2/apps/``

        Get applications

        :param app_id: Application id or name
        :type app_id: str

        :Keyword Arguments:
            * **query_args** (`Optional[SearchFilter]`)
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: List of application information
        :rtype: List[dict]
        """
        return SimbaRequest(
            endpoint=Path.APPS, query_params=query_args, login=login
        ).retrieve_sync(config=config)

    def get_application(
        self,
        org: str,
        app_id: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        GET ``/v2/apps/{application}/``

        Get application information

        :param org: organisation id or name
        :type org: str
        :param app_id: Application id or name
        :type app_id: str

        :Keyword Arguments:
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: Application information
        :rtype: dict
        """
        return GetRequest(endpoint=Path.APP.format(org, app_id), login=login).get_sync(
            config=config
        )

    def list_application_transactions(
        self,
        app_id: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> Generator[List[dict], None, None]:
        """
        GET ``/v2/apps/{application}/transactions/``

        List application transactions

        :param app_id: Application id or name
        :type app_id: str

        :Keyword Arguments:
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: Generator of application information
        :rtype: Generator[List[dict], None, None]
        """
        return SimbaRequest(
            endpoint=Path.APP_TXNS.format(app_id), login=login
        ).retrieve_iter_sync(config=config)

    def get_application_transactions(
        self,
        app_id: str,
        query_args: Optional[SearchFilter] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> List[dict]:
        """
        GET ``/v2/apps/{application}/transactions/``

        Get application transactions

        :param app_id: Application id or name
        :type app_id: str

        :Keyword Arguments:
            * **query_args** (`Optional[SearchFilter]`)
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: List of application information
        :rtype: List[dict]
        """
        return SimbaRequest(
            endpoint=Path.APP_TXNS.format(app_id), query_params=query_args, login=login
        ).retrieve_sync(config=config)

    def get_application_contract(
        self,
        app_id: str,
        contract_name: str,
        query_args: Optional[SearchFilter] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        GET ``/v2/apps/{application}/contract/{contract_name}/``

        Get contract information

        :param app_id: Application id or name
        :type app_id: str
        :param contract_name: Contract API name
        :type contract_name: str

        :Keyword Arguments:
            * **query_args** (`Optional[SearchFilter]`)
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: Contract information
        :rtype: dict
        """
        return GetRequest(
            endpoint=Path.APP_CONTRACT.format(app_id, contract_name),
            query_params=query_args,
            login=login,
        ).get_sync(config=config)

    def list_contract_transactions(
        self,
        app_id: str,
        contract_name: str,
        query_args: Optional[SearchFilter] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> Generator[List[dict], None, None]:
        """
        GET ``/v2/apps/{application}/contract/{contract_name}/transactions/``

        List contract transactions

        :param app_id: Application id or name
        :type app_id: str
        :param contract_name: Contract API name
        :type contract_name: str

        :Keyword Arguments:
            * **query_args** (`Optional[SearchFilter]`)
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: Generator of contract transactions
        :rtype: Generator[List[dict], None, None]
        """
        return SimbaRequest(
            endpoint=Path.CONTRACT_TXNS.format(app_id, contract_name),
            query_params=query_args,
            login=login,
        ).retrieve_iter_sync(config=config)

    def get_contract_transactions(
        self,
        app_id: str,
        contract_name: str,
        query_args: Optional[SearchFilter] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> List[dict]:
        """
        GET ``/v2/apps/{application}/contract/{contract_name}/transactions/``

        Get contract transactions

        :param app_id: Application id or name
        :type app_id: str
        :param contract_name: Contract API name
        :type contract_name: str

        :Keyword Arguments:
            * **query_args** (`Optional[SearchFilter]`)
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: List of contract transactions
        :rtype: List[dict]
        """
        return SimbaRequest(
            endpoint=Path.CONTRACT_TXNS.format(app_id, contract_name),
            query_params=query_args,
            login=login,
        ).retrieve_sync(config=config)

    def list_contracts(
        self,
        app_id: str,
        query_args: Optional[SearchFilter] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> Generator[List[dict], None, None]:
        """
        GET ``/v2/apps/{application}/contracts/``

        List contracts

        :param app_id: Application id or name
        :type app_id: str

        :Keyword Arguments:
            * **query_args** (`Optional[SearchFilter]`)
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: Generator of contracts
        :rtype: Generator[List[dict], None, None]
        """
        return SimbaRequest(
            endpoint=Path.APP_CONTRACTS.format(app_id),
            query_params=query_args,
            login=login,
        ).retrieve_iter_sync(config=config)

    def get_contracts(
        self,
        app_id: str,
        query_args: Optional[SearchFilter] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> List[dict]:
        """
        GET ``/v2/apps/{application}/contracts/``

        Get contracts

        :param app_id: Application id or name
        :type app_id: str

        :Keyword Arguments:
            * **query_args** (`Optional[SearchFilter]`)
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: List of contracts
        :rtype: List[dict]
        """
        return SimbaRequest(
            endpoint=Path.APP_CONTRACTS.format(app_id),
            query_params=query_args,
            login=login,
        ).retrieve_sync(config=config)

    def validate_bundle(
        self,
        app_id: str,
        contract_name: str,
        bundle_hash: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        GET ``/v2/apps/{application}/validate/{contract_name}/{bundle_hash}/``

        Validate the files in a bundle. Errors are given in the ``errors`` field of the response.

        :param app_id: Application id or name
        :type app_id: str
        :param contract_name: Contract API name
        :type contract_name: str
        :param bundle_hash: bundle hash
        :type bundle_hash: str

        :Keyword Arguments:
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: Validation information
        :rtype: dict
        """
        return GetRequest(
            endpoint=Path.VALIDATE_BUNDLE.format(app_id, contract_name, bundle_hash),
            login=login,
        ).get_sync(config=config)

    def get_bundle(
        self,
        app_id: str,
        contract_name: str,
        bundle_hash: str,
        download_location: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ):
        """
        GET ``/v2/apps/{application}/contract/{contract_name}/bundle/{bundle_hash}/``

        Get a bundle for a given bundle hash. The ``download_location`` parameter should be a local
        file location (including full file name and extension (tar.gz)) to write the bundle to.

        :param app_id: Application id or name
        :type app_id: str
        :param contract_name: Contract API name
        :type contract_name: str
        :param bundle_hash: bundle hash
        :type bundle_hash: str
        :param download_location: bundle hash
        :type download_location: str

        :Keyword Arguments:
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: None
        :rtype: None
        """
        return GetRequest(
            endpoint=Path.BUNDLE.format(app_id, contract_name, bundle_hash), login=login
        ).download_sync(location=download_location, config=config)

    def get_bundle_file(
        self,
        app_id: str,
        contract_name: str,
        bundle_hash: str,
        file_name: str,
        download_location: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ):
        """
        GET ``/v2/apps/{application}/contract/{contract_name}/bundle/{bundle_hash}/filename/{file_name}/``

        Get a file inside a bundle for a given bundle hash. The ``download_location`` parameter should be a local
        file location (including full file name and extension) to write the file to.

        :param app_id: Application id or name
        :type app_id: str
        :param contract_name: Contract API name
        :type contract_name: str
        :param bundle_hash: bundle hash
        :type bundle_hash: str
        :param file_name: the file name of the file in the bundle
        :type file_name: str
        :param download_location: bundle hash
        :type download_location: str

        :Keyword Arguments:
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: None
        :rtype: None
        """
        return GetRequest(
            endpoint=Path.BUNDLE_FILE.format(
                app_id, contract_name, bundle_hash, file_name
            ),
            login=login,
        ).download_sync(location=download_location, config=config)

    def get_manifest_for_bundle_from_bundle_hash(
        self,
        app_id: str,
        contract_name: str,
        bundle_hash: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ):
        """
        GET ``/v2/apps/{application}/contract/{contract_name}/bundle/{bundle_hash}/manifest/``

        Get the JSON manifest for a given bundle hash.

        :param app_id: Application id or name
        :type app_id: str
        :param contract_name: Contract API name
        :type contract_name: str
        :param bundle_hash: bundle hash
        :type bundle_hash: str

        :Keyword Arguments:
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: JSON Manifest
        :rtype: dict
        """
        return GetRequest(
            endpoint=Path.BUNDLE_MANIFEST.format(app_id, contract_name, bundle_hash),
            login=login,
        ).get_sync(config=config)

    """
    GET
    /v2/apps/{application}/contract/{contract_name}/info/
    list contract info ContractInfo
    """

    def get_contract_info(
        self,
        app_id: str,
        contract_name: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ):
        """
        GET ``/v2/apps/{application}/contract/{contract_name}/info/``

        Get Contract info JSON.

        :param app_id: Application id or name
        :type app_id: str
        :param contract_name: Contract API name
        :type contract_name: str

        :Keyword Arguments:
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: JSON Contract Info
        :rtype: dict
        """
        return GetRequest(
            endpoint=Path.CONTRACT_INFO.format(app_id, contract_name), login=login
        ).get_sync(config=config)

    def list_events(
        self,
        app_id: str,
        contract_name: str,
        event_name: Optional[str] = None,
        query_args: Optional[SearchFilter] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> Generator[List[dict], None, None]:
        """
        GET ``/v2/apps/{application}/contract/{contract}/events/{event_name}/``

        Get Contract info JSON.

        :param app_id: Application id or name
        :type app_id: str
        :param contract_name: Contract API name
        :type contract_name: str

        :Keyword Arguments:
            * **event_name** (`Optional[str]`)
            * **query_args** (`Optional[SearchFilter]`)
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: A generator of events
        :rtype: Generator[List[dict], None, None]
        """
        query_args = self.add_event_name(event_name=event_name, query_args=query_args)
        return SimbaRequest(
            endpoint=Path.CONTRACT_EVENTS.format(app_id, contract_name),
            query_params=query_args,
            login=login,
        ).retrieve_iter_sync(config=config)

    def get_events(
        self,
        app_id: str,
        contract_name: str,
        event_name: Optional[str] = None,
        query_args: Optional[SearchFilter] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> List[dict]:
        """
        GET ``/v2/apps/{application}/contract/{contract}/events/{event_name}/``

        Get Contract info JSON.

        :param app_id: Application id or name
        :type app_id: str
        :param contract_name: Contract API name
        :type contract_name: str

        :Keyword Arguments:
            * **event_name** (`Optional[str]`)
            * **query_args** (`Optional[SearchFilter]`)
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: A list of events
        :rtype: List[dict]
        """
        query_args = self.add_event_name(event_name=event_name, query_args=query_args)
        return SimbaRequest(
            endpoint=Path.CONTRACT_EVENTS.format(app_id, contract_name),
            query_params=query_args,
            login=login,
        ).retrieve_sync(config=config)

    def get_receipt(
        self,
        app_id: str,
        contract_name: str,
        receipt_hash: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ):
        """
        GET ``/v2/apps/{application}/contract/{contract_name}/receipt/{hash}/``

        Get a receipt from chain.

        :param app_id: Application id or name
        :type app_id: str
        :param contract_name: Contract API name
        :type contract_name: str
        :param receipt_hash: The hash of the receipt
        :type receipt_hash: str

        :Keyword Arguments:
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: A receipt
        :rtype: dict
        """
        return GetRequest(
            endpoint=Path.CONTRACT_RECEIPT.format(app_id, contract_name, receipt_hash),
            login=login,
        ).get_sync(config=config)

    def get_transaction(
        self,
        app_id: str,
        contract_name: str,
        transaction_hash: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ):
        """
        GET ``/v2/apps/{application}/contract/{contract_name}/transaction/{hash}/``

        Get a transaction from chain.

        :param app_id: Application id or name
        :type app_id: str
        :param contract_name: Contract API name
        :type contract_name: str
        :param transaction_hash: The hash of the receipt
        :type transaction_hash: str

        :Keyword Arguments:
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: A transaction
        :rtype: dict
        """
        return GetRequest(
            endpoint=Path.CONTRACT_TXN.format(app_id, contract_name, transaction_hash),
            login=login,
        ).get_sync(config=config)

    def get_transaction_by_id(
        self,
        org_name: str,
        transaction_id: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        GET ``/v2/organisations/{org_name}/transactions/{transaction_id}/``

        Get a transaction by id.

        :param org_name: Organisation id or name
        :param transaction_id: The ID of the transaction

        :Keyword Arguments:
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: A transaction
        :rtype: dict
        """
        return GetRequest(
            endpoint=Path.ORG_TXN.format(org_name, transaction_id),
            login=login,
        ).get_sync(config=config)

    def get_transactions_by_method(
        self,
        app_id: str,
        contract_name: str,
        method_name: str,
        query_args: Optional[SearchFilter] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> List[dict]:
        """
        GET ``/v2/apps/{application}/contract/{contract_name}/{method_name}/``

        Get transactions for a given method.

        :param app_id: Application id or name
        :type app_id: str
        :param contract_name: Contract API name
        :type contract_name: str
        :param method_name: The method name
        :type method_name: str

        :Keyword Arguments:
            * **query_args** (`Optional[SearchFilter]`)
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: A list of transactions
        :rtype: List[dict]
        """
        return SimbaRequest(
            endpoint=Path.CONTRACT_METHOD.format(app_id, contract_name, method_name),
            query_params=query_args,
            login=login,
        ).retrieve_sync(config=config)

    def list_transactions_by_method(
        self,
        app_id: str,
        contract_name: str,
        method_name: str,
        query_args: Optional[SearchFilter] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> Generator[List[dict], None, None]:
        """
        GET ``/v2/apps/{application}/contract/{contract_name}/{method_name}/``

        List transactions for a given method.

        :param app_id: Application id or name
        :type app_id: str
        :param contract_name: Contract API name
        :type contract_name: str
        :param method_name: The method name
        :type method_name: str

        :Keyword Arguments:
            * **query_args** (`Optional[SearchFilter]`)
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: A generator of transactions
        :rtype: Generator[List[dict], None, None]
        """
        return SimbaRequest(
            endpoint=Path.CONTRACT_METHOD.format(app_id, contract_name, method_name),
            query_params=query_args,
            login=login,
        ).retrieve_iter_sync(config=config)

    def get_transactions_by_contract(
        self,
        app_id: str,
        contract_name: str,
        query_args: Optional[SearchFilter] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> List[dict]:
        """
        GET ``/v2/apps/{application}/contract/{contract_name}/transactions/``

        Get transactions for a contract. Note that filters must be consistent across contract methods.

        :param app_id: Application id or name
        :type app_id: str
        :param contract_name: Contract API name
        :type contract_name: str

        :Keyword Arguments:
            * **query_args** (`Optional[SearchFilter]`)
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: A list of transactions
        :rtype: List[dict]
        """
        return SimbaRequest(
            endpoint=Path.CONTRACT_TXNS.format(app_id, contract_name),
            query_params=query_args,
            login=login,
        ).retrieve_sync(config=config)

    def list_transactions_by_contract(
        self,
        app_id: str,
        contract_name: str,
        query_args: Optional[SearchFilter] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> Generator[List[dict], None, None]:
        """
        GET ``/v2/apps/{application}/contract/{contract_name}/transactions/``

        List transactions for a contract. Note that filters must be consistent across contract methods.

        :param app_id: Application id or name
        :type app_id: str
        :param contract_name: Contract API name
        :type contract_name: str

        :Keyword Arguments:
            * **query_args** (`Optional[SearchFilter]`)
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: A generator of transactions
        :rtype: Generator[List[dict], None, None]
        """
        return SimbaRequest(
            endpoint=Path.CONTRACT_TXNS.format(app_id, contract_name),
            query_params=query_args,
            login=login,
        ).retrieve_iter_sync(config=config)

    def get_events_by_contract(
        self,
        app_id: str,
        contract_name: str,
        event_name: Optional[str] = None,
        query_args: Optional[SearchFilter] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> List[dict]:
        """
        GET ``/v2/apps/{application}/contract/{contract_name}/events/{event_name}``

        Get events for a contract with the given event type name.

        :param app_id: Application id or name
        :type app_id: str
        :param contract_name: Contract API name
        :type contract_name: str

        :Keyword Arguments:
            * **event_name** (`Optional[str]`)
            * **query_args** (`Optional[SearchFilter]`)
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: A list of transactions
        :rtype: List[dict]
        """
        query_args = self.add_event_name(event_name=event_name, query_args=query_args)
        return SimbaRequest(
            endpoint=Path.CONTRACT_EVENTS.format(app_id, contract_name),
            query_params=query_args,
            login=login,
        ).retrieve_sync(config=config)

    def list_events_by_contract(
        self,
        app_id: str,
        contract_name: str,
        event_name: Optional[str] = None,
        query_args: Optional[SearchFilter] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> Generator[List[dict], None, None]:
        """
        GET ``/v2/apps/{application}/contract/{contract_name}/events/{event_name}``

        List events for a contract with the given event type name.

        :param app_id: Application id or name
        :type app_id: str
        :param contract_name: Contract API name
        :type contract_name: str

        :Keyword Arguments:
            * **event_name** (`Optional[str]`)
            * **query_args** (`Optional[SearchFilter]`)
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: A generator of transactions
        :rtype: Generator[List[dict], None, None]
        """
        query_args = self.add_event_name(event_name=event_name, query_args=query_args)
        return SimbaRequest(
            endpoint=Path.CONTRACT_EVENTS.format(app_id, contract_name),
            query_params=query_args,
            login=login,
        ).retrieve_iter_sync(config=config)

    def submit_contract_method(
        self,
        app_id: str,
        contract_name: str,
        method_name: str,
        inputs: Optional[dict] = None,
        headers: Optional[dict] = None,
        files: Optional[FileDict] = None,
        txn_headers: TxnHeaders = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        POST ``/v2/apps/{application}/contract/{contract_name}/{method_name}/``

        Submit a transaction to a contract method. This calls the async endpoint and
        the returned transaction will have a state of ACCEPTED and will not contain the transaction hash.

        :param app_id: Application id or name
        :type app_id: str
        :param contract_name: Contract API name
        :type contract_name: str
        :param method_name: Method name
        :type method_name: str

        :Keyword Arguments:
            * **inputs** (`Optional[dict]`) - method parameters as a dictionary
            * **headers** (`Optional[dict]`) - additional http headers
            * **files** (`Optional[FileDict]`) - optional off chain files to upload
            * **txn_headers** (`Optional[TxnHeaders]`) - optional transaction related headers to include
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: The transaction
        :rtype: dict
        """
        headers = headers or {}
        headers.update(txn_headers.as_headers() if txn_headers else {})
        inputs = inputs if inputs else {}
        result = PostRequest(
            endpoint=Path.CONTRACT_METHOD.format(app_id, contract_name, method_name),
            login=login,
        ).post_sync(json_payload=inputs, files=files, headers=headers, config=config)
        return result

    def call_contract_method(
        self,
        app_id: str,
        contract_name: str,
        method_name: str,
        args: Optional[MethodCallArgs] = None,
        headers: Optional[dict] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        GET ``/v2/apps/{application}/contract/{contract_name}/{method_name}/``

        Call a contract getter method.

        :param app_id: Application id or name
        :type app_id: str
        :param contract_name: Contract API name
        :type contract_name: str
        :param method_name: Method name
        :type method_name: str

        :Keyword Arguments:
            * **args** (`Optional[MethodCallArgs]`) - optional method parameters as a dict
            * **headers** (`Optional[dict]`) - additional http headers
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: The getter response. The `value` field contains the result.
        :rtype: dict
        """
        headers = headers or {}
        return GetRequest(
            endpoint=Path.CONTRACT_METHOD.format(app_id, contract_name, method_name),
            login=login,
        ).call_sync(config=config, args=args, headers=headers)

    def submit_contract_method_sync(
        self,
        app_id: str,
        contract_name: str,
        method_name: str,
        inputs: Optional[dict] = None,
        headers: Optional[dict] = None,
        files: FileDict = None,
        txn_headers: TxnHeaders = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        POST ``/v2/apps/{application}/sync/contract/{contract_name}/{method_name}/``

        Submit a transaction to a contract method. This calls the sync endpoint and
        the returned transaction will have a state of SUBMITTED and will contain the transaction hash.

        :param app_id: Application id or name
        :type app_id: str
        :param contract_name: Contract API name
        :type contract_name: str
        :param method_name: Method name
        :type method_name: str

        :Keyword Arguments:
            * **inputs** (`Optional[dict]`) - method parameters as a dictionary
            * **headers** (`Optional[dict]`) - additional http headers
            * **files** (`Optional[FileDict]`) - optional off chain files to upload
            * **txn_headers** (`Optional[TxnHeaders]`) - optional transaction related headers to include
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: The transaction
        :rtype: dict
        """
        headers = headers or {}
        headers.update(txn_headers.as_headers() if txn_headers else {})
        inputs = inputs if inputs else {}
        result = PostRequest(
            endpoint=Path.SYNC_CONTRACT_METHOD.format(
                app_id, contract_name, method_name
            ),
            login=login,
        ).post_sync(json_payload=inputs, files=files, headers=headers, config=config)
        return result

    # TODO(Adam): Make a transaction object to assist the user. Right now it's just a dict
    def submit_signed_transaction(
        self,
        app_id: str,
        txn_id: str,
        txn: dict,
        headers: Optional[dict] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ):
        """
        PATCH ``/v2/apps/{application}/transactions/{identifier}/``

        Submit a signed transaction to a contract method.

        :param app_id: Application id or name
        :type app_id: str
        :param txn_id: The ID of the transaction in the database
        :type txn_id: str
        :param txn: The signed transaction keyed to the ``transaction`` value.
        :type txn: dict

        :Keyword Arguments:
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: The transaction
        :rtype: dict
        """
        headers = headers or {}
        return PatchRequest(
            endpoint=Path.APP_TXN.format(app_id, txn_id), login=login
        ).patch_sync(json_payload={"transaction": txn}, config=config, headers=headers)

    def save_design(
        self,
        org: str,
        name: str,
        code: Union[str, dict],
        design_id: Optional[str] = None,
        target_contract: str = None,
        libraries: dict = None,
        encode: bool = True,
        model: str = None,
        extras: Optional[dict] = None,
        binary_targets: List[str] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        POST/PUT ``/v2/organisations/{organisation}/contract_designs/``

        Save a contract design, aka the code. If the design ID is given, this results in an update via a PUT.
        Otherwise, a new design is created via a POST.

        :param org: The organisation to save to.
        :type org: str
        :param name: The name of the design.
        :type name: str
        :param code: the code
        :type code: Union[str, dict]

        :Keyword Arguments:
            * **design_id** (`str`) - A design ID. If provided, this will update the given design via a PUT. Otherwise a new design will be created.
            * **target_contract** (`str`) - The name of the target contract to create an API for
            * **libraries** (`dict`) - Libraries that are already deployed the contract may depend on
            * **encode** (`bool`) - whether or not the code needs to be still encoded to base64. Default is true.
            * **model** (`str`) - The model to use when generating metadata. This defaults to `aat`, the SIMBA default.
            * **binary_targets** (`List[str]`) - A list of contracts to return byte code for.
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: the design object
        :rtype: dict
        """
        if encode:
            if isinstance(code, dict):
                tmp = {}
                for k, v in code.items():
                    tmp[k] = base64.b64encode(v.encode()).decode("utf-8")
                code = tmp
            else:
                code = base64.b64encode(code.encode()).decode("utf-8")
        full = {"name": name, "code": code, "language": "solidity"}
        if target_contract:
            full["target_contract"] = target_contract
        if libraries is not None:
            full["libraries"] = libraries
        if model is not None:
            full["model"] = model
        if binary_targets is not None:
            full["binary_targets"] = binary_targets
        if extras is not None:
            full["extras"] = extras
        if not config:
            config = ConnectionConfig()
        if config.timeout < 120:  # while this is sync, we need to be patient
            config.timeout = 120
        if design_id:
            return PutRequest(
                endpoint=Path.DESIGN.format(org, design_id), login=login
            ).put_sync(json_payload=full, config=config)
        else:
            return PostRequest(
                endpoint=Path.DESIGNS.format(org), login=login
            ).post_sync(json_payload=full, config=config)

    def wait_for_deployment(
        self,
        org: str,
        uid: str,
        total_time: int = 0,
        max_time: int = 960,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        GET ``/v2/organisations/{organisation}/deployments/{deployment_id}/``

        Wait for a deployment to complete, i.e., it's state becomes COMPLETED.

        :param org: The organisation to save to.
        :type org: str
        :param uid: The ID of the deployment resource
        :type uid: str

        :Keyword Arguments:
            * **total_time** (`int`) - total time waited so far. leave this at zero as it gets incremented through
                                        recursive calls.
            * **max_time** (`int`) - maximum seconds ot wait. Default is 480
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: The deployment object
        :rtype: dict
        """
        res = GetRequest(
            endpoint=Path.DEPLOYMENT.format(org, uid), login=login
        ).get_sync(config=config)
        state = res["state"]
        if state == "COMPLETED":
            return res
        else:
            if total_time > max_time:
                raise ValueError("[wait_for_deployment] :: waited way too long")
            time.sleep(2)
            total_time += 2
            return self.wait_for_deployment(
                org,
                uid,
                total_time=total_time,
                max_time=max_time,
                login=login,
                config=config,
            )

    def deploy_design(
        self,
        org: str,
        app: str,
        api_name: str,
        design_id: str,
        blockchain: str,
        storage="no_storage",
        display_name=None,
        args=None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        POST ``/v2/organisations/{organisation}/contract_designs/deploy/``

        Deploy a contract design. This results in an artifact being created from the design
        and a deployment object being created and returned.

        :param org: The organisation to deploy to.
        :type org: str
        :param app: The app to deploy to.
        :type org: str
        :param api_name: The api name of the contract.
        :type api_name: str
        :param design_id: The id of the design to deploy
        :type design_id: str
        :param blockchain: The name of the blockchain to deploy to.
        :type blockchain: str

        :Keyword Arguments:
            * **storage** (`str`) - The name of the off chain storage to use. Defaults to `no_storage`
            * **display_name** (`str`) - Display name for the contract.
            * **args** (`dict`) - Constructor args for the deployment.
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: A deployment object
        :rtype: Deployment
        """
        full = {"blockchain": blockchain, "storage": storage, "api_name": api_name}
        if display_name:
            full["display_name"] = display_name
        full["app_name"] = app
        if args:
            full["args"] = args
        return PostRequest(
            endpoint=Path.DESIGN_DEPLOY.format(org, design_id),
            login=login,
        ).post_sync(json_payload=full, config=config)

    def deploy_artifact(
        self,
        org: str,
        app: str,
        api_name: str,
        artifact_id: str,
        blockchain: str,
        storage="no_storage",
        display_name=None,
        args=None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        POST ``/v2/organisations/{organisation}/deployments/``

        Deploy a contract artifact. This results in a deployment object being created and returned.

        :param org: The organisation to deploy to.
        :type org: str
        :param app: The app to deploy to.
        :type app: str
        :param api_name: The api name of the contract.
        :type api_name: str
        :param artifact_id: The id of the artifact to deploy
        :type artifact_id: str
        :param blockchain: The name of the blockchain to deploy to.
        :type blockchain: str

        :Keyword Arguments:
            * **storage** (`str`) - The name of the off chain storage to use. Defaults to `no_storage`
            * **display_name** (`str`) - Display name for the contract.
            * **args** (`dict`) - Constructor args for the deployment.
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: A deployment object
        :rtype: Deployment
        """
        full = {
            "blockchain": blockchain,
            "storage": storage,
            "api_name": api_name,
            "artifact_id": artifact_id,
        }
        if display_name:
            full["display_name"] = display_name
        full["app_name"] = app
        if args:
            full["args"] = args
        return PostRequest(
            endpoint=Path.DEPLOYMENTS.format(org),
            login=login,
        ).post_sync(json_payload=full, config=config)

    def deploy_library(
        self,
        org: str,
        lib_name: str,
        blockchain: str,
        code: str,
        encode: bool = True,
        app_name=None,
        args=None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        POST ``/v2/organisations/{organisation}/deployments/library/``

        Deploy a library. This results in a deployment object being created and returned.

        :param org: The organisation to deploy to.
        :type org: str
        :param code: The library code.
        :type code: str
        :param lib_name: The name of the library.
        :type lib_name: str
        :param blockchain: The name of the blockchain to deploy to.
        :type blockchain: str
        :param encode: whether to base64 encode the code or not.
        :type encode: bool

        :Keyword Arguments:
            * **app_name** (`str`) - App name for the library.
            * **args** (`dict`) - Constructor args for the deployment.
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: A deployment object
        :rtype: Deployment
        """
        if encode:
            code = base64.b64encode(code.encode()).decode("utf-8")
        full = {
            "blockchain": blockchain,
            "language": "solidity",
            "code": code,
            "lib_name": lib_name,
        }
        if app_name:
            full["app_name"] = app_name
        if args:
            full["args"] = args
        return PostRequest(
            endpoint=Path.LIBRARIES.create(org),
            login=login,
        ).post_sync(json_payload=full, config=config)

    def wait_for_deploy_library(
        self,
        org: str,
        lib_name: str,
        blockchain: str,
        code: str,
        app_name=None,
        args=None,
        encode: bool = True,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> Tuple[str, str]:
        """
        POST ``/v2/organisations/{organisation}/deployments/library/``

        Deploy a library and wait for completion.
        This results in a deployment object being created and returned.

        :param org: The organisation to deploy to.
        :type org: str
        :param code: The library code.
        :type code: str
        :param lib_name: The name of the library.
        :type lib_name: str
        :param blockchain: The name of the blockchain to deploy to.
        :type blockchain: str
        :param encode: whether to base64 encode the code or not.
        :type encode: bool

        :Keyword Arguments:
            * **app_name** (`str`) - App name for the library.
            * **args** (`dict`) - Constructor args for the deployment.
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: A tuple of address and contract ID
        :rtype: Tuple[str, str]
        """
        res = self.deploy_library(
            org=org,
            lib_name=lib_name,
            blockchain=blockchain,
            code=code,
            args=args,
            app_name=app_name,
            encode=encode,
            login=login,
            config=config,
        )
        deployment_id = res["deployment_id"]
        try:
            deployed = self.wait_for_deployment(org, deployment_id)
            address = get_address_by_name(deployed, lib_name)
            library_id = get_deployed_artifact_id(deployed)
        except Exception as ex:
            logger.warning(
                "[wait_for_deploy_library] :: failed to wait for deployment: {}".format(
                    ex
                )
            )
            address = None
            library_id = None
        return address, library_id

    def wait_for_deploy_design(
        self,
        org: str,
        app: str,
        design_id: str,
        api_name: str,
        blockchain: str,
        storage: Optional[str] = "no_storage",
        display_name: str = None,
        args: Optional[dict] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> Tuple[str, str]:
        """
        POST ``/v2/organisations/{organisation}/contract_designs/deploy/``

        Deploy a contract design and wait for it to complete. This returns the address
        of the deployed contract and contract DB ID

        :param org: The organisation to deploy to.
        :type org: str
        :param app: The app to deploy to.
        :type org: str
        :param design_id: The id of the design to deploy
        :type design_id: str
        :param api_name: The api name of the contract.
        :type api_name: str
        :param blockchain: The name of the blockchain to deploy to.
        :type blockchain: str

        :Keyword Arguments:
            * **storage** (`str`) - The name of the off chain storage to use. Defaults to `no_storage`
            * **display_name** (`str`) - Display name for the contract.
            * **args** (`dict`) - Constructor args for the deployment.
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: A tuple of address and contract ID
        :rtype: Tuple[str, str]
        """
        res = self.deploy_design(
            org=org,
            app=app,
            api_name=api_name,
            design_id=design_id,
            blockchain=blockchain,
            storage=storage,
            args=args,
            display_name=display_name,
            login=login,
            config=config,
        )
        deployment_id = res["deployment_id"]
        try:
            deployed = self.wait_for_deployment(org, deployment_id)
            address = get_address(deployed)
            contract_id = get_deployed_artifact_id(deployed)
        except Exception as ex:
            logger.warning("[deploy] :: failed to wait for deployment: {}".format(ex))
            address = None
            contract_id = None
        return address, contract_id

    def wait_for_deploy_artifact(
        self,
        org: str,
        app: str,
        artifact_id: str,
        api_name: str,
        blockchain: str,
        storage: Optional[str] = "no_storage",
        display_name: str = None,
        args: Optional[dict] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> Tuple[str, str]:
        """
        POST ``/v2/organisations/{organisation}/contract_artifacts/``

        Deploy a contract artifact and wait for it to complete. This returns the address
        of the deployed contract and contract DB ID

        :param org: The organisation to deploy to.
        :type org: str
        :param app: The app to deploy to.
        :type org: str
        :param artifact_id: The id of the artifact to deploy
        :type artifact_id: str
        :param api_name: The api name of the contract.
        :type api_name: str
        :param blockchain: The name of the blockchain to deploy to.
        :type blockchain: str

        :Keyword Arguments:
            * **storage** (`str`) - The name of the off chain storage to use. Defaults to `no_storage`
            * **display_name** (`str`) - Display name for the contract.
            * **args** (`dict`) - Constructor args for the deployment.
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: A tuple of address and contract ID
        :rtype: Tuple[str, str]
        """
        res = self.deploy_artifact(
            org=org,
            app=app,
            api_name=api_name,
            artifact_id=artifact_id,
            blockchain=blockchain,
            storage=storage,
            args=args,
            display_name=display_name,
            login=login,
            config=config,
        )
        deployment_id = res["id"]
        try:
            deployed = self.wait_for_deployment(org, deployment_id)
            address = get_address(deployed)
            contract_id = get_deployed_artifact_id(deployed)
        except Exception as ex:
            logger.warning("[deploy] :: failed to wait for deployment: {}".format(ex))
            address = None
            contract_id = None
        return address, contract_id

    def get_designs(
        self,
        org: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> List[dict]:
        """
        GET ``/v2/organisations/{organisation}/contract_designs/``

        Get contract designs for an organisation.

        :param org: The organisation.
        :type org: str

        :Keyword Arguments:
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: The designs
        :rtype: List[dict]
        """
        return SimbaRequest(
            endpoint=Path.DESIGNS.format(org),
            login=login,
        ).retrieve_sync(config=config)

    def get_artifacts(
        self,
        org: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> List[dict]:
        """
        GET ``/v2/organisations/{organisation}/contract_artifacts/``

        Get contract artifacts for an organisation.

        :param org: The organisation.
        :type org: str

        :Keyword Arguments:
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: The artifacts
        :rtype: List[dict]
        """
        return SimbaRequest(
            endpoint=Path.CONTRACT_ARTIFACTS.format(org),
            login=login,
        ).retrieve_sync(config=config)

    def get_artifact(
        self,
        org: str,
        artifact_id: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        GET ``/v2/organisations/{organisation}/contract_artifacts/{artifact_id}``

        Get a contract artifacts in an organisation.

        :param org: The organisation.
        :type org: str
        :param artifact_id: The organisation to save to.
        :type artifact_id: str

        :Keyword Arguments:
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: The artifact object
        :rtype: dict
        """
        return GetRequest(
            endpoint=Path.CONTRACT_ARTIFACT.format(org, artifact_id),
            login=login,
        ).get_sync(config=config)

    def create_artifact(
        self,
        org: str,
        design_id: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        POST ``/v2/organisations/{organisation}/contract_artifacts/``

        Create contract artifacts for an organisation.

        :param org: The organisation.
        :type org: str
        :param design_id: The contract design id from which to derive the artifact.
        :type design_id: str

        :Keyword Arguments:
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: The artifact object
        :rtype: dict
        """
        inputs = {"design_id": design_id}
        return PostRequest(
            endpoint=Path.CONTRACT_ARTIFACTS.format(org),
            login=login,
        ).post_sync(config=config, json_payload=inputs)

    def get_blockchains(
        self,
        org: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> List[dict]:
        """
        GET ``/v2/organisations/{organisation}/blockchains/``

        Get blockchains for an organisation.

        :param org: The organisation.
        :type org: str

        :Keyword Arguments:
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: The blockchain objects
        :rtype: List[dict]
        """
        return SimbaRequest(
            endpoint=Path.BLOCKCHAINS.format(org),
            login=login,
        ).retrieve_sync(config=config)

    def get_storage(
        self,
        org: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> List[dict]:
        """
        GET ``/v2/organisations/{organisation}/storage/``

        Get off chain storage repositories for an organisation.

        :param org: The organisation.
        :type org: str

        :Keyword Arguments:
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: The storage objects
        :rtype: List[dict]
        """
        return SimbaRequest(
            endpoint=Path.STORAGES.format(org),
            login=login,
        ).retrieve_sync(config=config)

    def get_abi(
        self,
        blockchain: str,
        contract_address: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        GET ``/services/blockchains/{blockchain}/contracts/{contract_address}/abi/``

        Get the ABI and metadata for a contract address.

        :param contract_address: The address of the deployed contract.
        :type contract_address: str
        :param blockchain: The name of the blockchain the contract is deployed on.
        :type blockchain: str

        :Keyword Arguments:
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: a Dict with keys `abi` and `metadata`.
        :rtype: dict
        """
        return SimbaRequest(
            endpoint=Path.CONTRACT_ABI.create(blockchain, contract_address),
            login=login,
        ).send_sync(config=config)

    def get_accounts(
        self,
        nickname: Optional[str] = None,
        alias: Optional[str] = None,
        network: Optional[str] = None,
        headers: Optional[dict] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> List[dict]:
        """
        GET ``/user/accounts/``

        Get the accounts for the current user. Optionally filter on
        nickname or alias.

        :Keyword Arguments:
            * **nickname** (`Optional[str]`)
            * **alias** (`Optional[str]`)
            * **network** (`Optional[str]`)
            * **headers** (`Optional[dict]`) additional http headers
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: a list of account objects
        :rtype: list
        """
        params = None
        if nickname or alias or network:
            params = SearchFilter()
            if nickname:
                params.add_filter(
                    FieldFilter(field="nickname", op=FilterOp.EQ, value=nickname)
                )
            if alias:
                params.add_filter(
                    FieldFilter(field="alias", op=FilterOp.EQ, value=alias)
                )
            if network:
                params.add_filter(
                    FieldFilter(field="networks", op=FilterOp.EQ, value=network)
                )
        return SimbaRequest(
            endpoint=Path.USER_ACCOUNTS,
            query_params=params,
            login=login,
        ).retrieve_sync(config=config, headers=headers or {})

    def get_account(
        self,
        uid: str,
        headers: Optional[dict] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        GET ``/user/accounts/{id}``

        Get the account for the current user with the given id.

        :Keyword Arguments:
            * **headers** (`Optional[dict]`) - additional http headers
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: an account object.
        :rtype: dict
        """
        return SimbaRequest(
            endpoint=Path.USER_ACCOUNT.format(uid),
            login=login,
        ).send_sync(config=config, headers=headers or {})

    def create_account(
        self,
        network_subtype: str,
        network: str,
        nickname: str,
        alias: str,
        network_type: Optional[str] = "ethereum",
        headers: Optional[dict] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        POST ``/user/accounts/``

        Create a new account for the current user.

        :param network_subtype: The blockchain subtype.
        :type network_subtype: str
        :param network: The blockchain name.
        :type network: str
        :param nickname: The account nickname.
        :type nickname: str
        :param alias: The account alias.
        :type alias: str

        :Keyword Arguments:
            * **headers** (`Optional[dict]`) - additional http headers
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: an account object.
        :rtype: dict
        """
        payload = {
            "network_type": network_type,
            "network_subtype": network_subtype,
            "network": network,
            "nickname": nickname,
            "alias": alias,
        }
        return SimbaRequest(
            method="POST",
            endpoint=Path.USER_ACCOUNTS,
            login=login,
        ).send_sync(config=config, json_payload=payload, headers=headers or {})

    def set_account(
        self,
        network_subtype: str,
        network: str,
        nickname: str,
        alias: str,
        address: str,
        private_key: str,
        network_type: Optional[str] = "ethereum",
        headers: Optional[dict] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        POST ``/user/accounts/set/``

        Create a new account for the current user.

        :param network_subtype: The blockchain subtype.
        :type network_subtype: str
        :param network: The blockchain name.
        :type network: str
        :param nickname: The account nickname.
        :type nickname: str
        :param alias: The account alias.
        :type alias: str
        :param address: The account address.
        :type address: str
        :param private_key: The account private key.
        :type private_key: str

        :Keyword Arguments:
            * **network_type** (`Optional[str]`)
            * **headers** (`Optional[dict]`) - additional http headers
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: an account object.
        :rtype: dict
        """
        payload = {
            "network_type": network_type,
            "network_subtype": network_subtype,
            "network": network,
            "nickname": nickname,
            "alias": alias,
            "public_key": address,
            "private_key": private_key,
        }
        return SimbaRequest(
            method="POST",
            endpoint=Path.USER_ACCOUNT_SET,
            login=login,
        ).send_sync(config=config, json_payload=payload, headers=headers or {})

    def account_sign(
        self,
        uid: str,
        input_pairs: List[Tuple[str, Any]],
        hash_message: Optional[bool] = False,
        headers: Optional[dict] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        POST ``/user/accounts/{account_id}/sign/``

        Sign a message using the specified account.

        :param uid: The account id.
        :type uid: str
        :param input_pairs: A list of tuples defining the data type and data to sign.
        :type input_pairs: List[Tuple(str, Any)]

        :Keyword Arguments:
            * **headers** (`Optional[dict]`) - additional http headers
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: a Dict with the signed content.
        :rtype: dict
        """
        payload = {
            "input_pairs": [list(t) for t in input_pairs],
            "hash_message": hash_message,
        }
        return SimbaRequest(
            method="POST",
            endpoint=Path.USER_ACCOUNT_SIGN.format(uid),
            login=login,
        ).send_sync(config=config, json_payload=payload, headers=headers or {})

    def account_address_sign(
        self,
        blockchain: str,
        address: str,
        input_pairs: List[Tuple[str, Any]],
        hash_message: Optional[bool] = False,
        headers: Optional[dict] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        POST ``/user/accounts/{account_id}/sign/``

        Sign a message using the specified account.

        :param org: The organisation.
        :type org: str
        :param blockchain: The blockchain.
        :type blockchain: str
        :param address: The account address.
        :type address: str
        :param input_pairs: A list of tuples defining the data type and data to sign.
        :type input_pairs: List[Tuple(str, Any)]

        :Keyword Arguments:
            * **headers** (`Optional[dict]`) - additional http headers
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: a Dict with the signed content.
        :rtype: dict
        """
        payload = {
            "input_pairs": [list(t) for t in input_pairs],
            "hash_message": hash_message,
        }
        return SimbaRequest(
            method="POST",
            endpoint=Path.USER_ACCOUNT_ADDRESS_SIGN.format(blockchain, address),
            login=login,
        ).send_sync(config=config, json_payload=payload, headers=headers or {})

    def admin_get_accounts(
        self,
        alias: Optional[str] = None,
        network: Optional[str] = None,
        owner_type: Optional[str] = None,
        owner_identifier: Optional[str] = None,
        headers: Optional[dict] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> List[dict]:
        """
        GET ``/admin/accounts/``

        Get the accounts for the current user. Optionally filter on
        nickname or alias.

        :Keyword Arguments:
            * **nickname** (`Optional[str]`)
            * **alias** (`Optional[str]`)
            * **network** (`Optional[str]`)
            * **owner_identifier** (`Optional[str]`)
            * **owner_type** (`Optional[str]`)
            * **headers** (`Optional[dict]`) additional http headers
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: a list of account objects
        :rtype: list
        """
        params = None
        if alias or network or owner_type:
            params = SearchFilter()
            if owner_type:
                params.add_filter(
                    FieldFilter(field="owner_type", op=FilterOp.EQ, value=owner_type)
                )
                if owner_identifier:
                    params.add_filter(
                        FieldFilter(
                            field="owner_identifier",
                            op=FilterOp.EQ,
                            value=owner_identifier,
                        )
                    )
            if alias:
                params.add_filter(
                    FieldFilter(field="alias", op=FilterOp.EQ, value=alias)
                )
            if network:
                params.add_filter(
                    FieldFilter(field="networks", op=FilterOp.EQ, value=network)
                )
        return SimbaRequest(
            endpoint=Path.ADMIN_ACCOUNTS,
            query_params=params.query,
            login=login,
        ).retrieve_sync(config=config, headers=headers or {})

    def get_org_accounts(
        self,
        org: str,
        nickname: Optional[str] = None,
        alias: Optional[str] = None,
        network: Optional[str] = None,
        headers: Optional[dict] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> List[dict]:
        """
        GET ``/v2/organisations/{org}/accounts/``

        Get the accounts for the current user. Optionally filter on
        nickname or alias.

        :param org: The organisation.
        :type org: str

        :Keyword Arguments:
            * **nickname** (`Optional[str]`)
            * **alias** (`Optional[str]`)
            * **network** (`Optional[str]`)
            * **headers** (`Optional[dict]`) additional http headers
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: a list of account objects
        :rtype: list
        """
        params = None
        if nickname or alias or network:
            params = SearchFilter()
            if nickname:
                params.add_filter(
                    FieldFilter(field="nickname", op=FilterOp.EQ, value=nickname)
                )
            if alias:
                params.add_filter(
                    FieldFilter(field="alias", op=FilterOp.EQ, value=alias)
                )
            if network:
                params.add_filter(
                    FieldFilter(field="networks", op=FilterOp.EQ, value=network)
                )
        return SimbaRequest(
            endpoint=Path.ORG_ACCOUNTS.create(org),
            query_params=params,
            login=login,
        ).retrieve_sync(config=config, headers=headers or {})

    def get_org_account(
        self,
        org: str,
        uid: str,
        headers: Optional[dict] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        GET ``/v2/organisations/{org}/accounts/{id}``

        Get the account for the current user with the given id.

        :param org: The organisation.
        :type org: str

        :Keyword Arguments:
            * **headers** (`Optional[dict]`) - additional http headers
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: an account object.
        :rtype: dict
        """
        return SimbaRequest(
            endpoint=Path.ORG_ACCOUNT.format(org, uid),
            login=login,
        ).send_sync(config=config, headers=headers or {})

    def create_org_account(
        self,
        org: str,
        network_subtype: str,
        network: str,
        nickname: str,
        alias: str,
        network_type: Optional[str] = "ethereum",
        headers: Optional[dict] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        POST ``/v2/organisations/{org}/accounts/``

        Create a new account for the current user.

        :param org: The organisation.
        :type org: str
        :param network_subtype: The blockchain subtype.
        :type network_subtype: str
        :param network: The blockchain name.
        :type network: str
        :param nickname: The account nickname.
        :type nickname: str
        :param alias: The account alias.
        :type alias: str

        :Keyword Arguments:
            * **headers** (`Optional[dict]`) - additional http headers
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: an account object.
        :rtype: dict
        """
        payload = {
            "network_type": network_type,
            "network_subtype": network_subtype,
            "network": network,
            "nickname": nickname,
            "alias": alias,
        }
        return SimbaRequest(
            method="POST",
            endpoint=Path.ORG_ACCOUNTS.create(org),
            login=login,
        ).send_sync(config=config, json_payload=payload, headers=headers or {})

    def set_org_account(
        self,
        org: str,
        network_subtype: str,
        network: str,
        nickname: str,
        alias: str,
        address: str,
        private_key: str,
        network_type: Optional[str] = "ethereum",
        headers: Optional[dict] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        POST ``/user/accounts/set/``

        Create a new account for the current user.

        :param org: The organisation.
        :type org: str
        :param network_subtype: The blockchain subtype.
        :type network_subtype: str
        :param network: The blockchain name.
        :type network: str
        :param nickname: The account nickname.
        :type nickname: str
        :param alias: The account alias.
        :type alias: str
        :param address: The account address.
        :type address: str
        :param private_key: The account private key.
        :type private_key: str

        :Keyword Arguments:
            * **network_type** (`Optional[str]`)
            * **headers** (`Optional[dict]`) - additional http headers
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: an account object.
        :rtype: dict
        """
        payload = {
            "network_type": network_type,
            "network_subtype": network_subtype,
            "network": network,
            "nickname": nickname,
            "alias": alias,
            "public_key": address,
            "private_key": private_key,
        }
        return SimbaRequest(
            method="POST",
            endpoint=Path.ORG_ACCOUNT_SET.create(org),
            login=login,
        ).send_sync(config=config, json_payload=payload, headers=headers or {})

    def org_account_sign(
        self,
        org: str,
        uid: str,
        input_pairs: List[Tuple[str, Any]],
        hash_message: Optional[bool] = False,
        headers: Optional[dict] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        POST ``/user/accounts/{account_id}/sign/``

        Sign a message using the specified account.

        :param org: The organisation.
        :type org: str
        :param uid: The account id.
        :type uid: str
        :param input_pairs: A list of tuples defining the data type and data to sign.
        :type input_pairs: List[Tuple(str, Any)]

        :Keyword Arguments:
            * **headers** (`Optional[dict]`) - additional http headers
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: a Dict with the signed content.
        :rtype: dict
        """
        payload = {
            "input_pairs": [list(t) for t in input_pairs],
            "hash_message": hash_message,
        }
        return SimbaRequest(
            method="POST",
            endpoint=Path.ORG_ACCOUNT_SIGN.create(org, uid),
            login=login,
        ).send_sync(config=config, json_payload=payload, headers=headers or {})

    def org_account_address_sign(
        self,
        org: str,
        blockchain: str,
        address: str,
        input_pairs: List[Tuple[str, Any]],
        hash_message: Optional[bool] = False,
        headers: Optional[dict] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        POST ``/user/accounts/{account_id}/sign/``

        Sign a message using the specified account.

        :param org: The organisation.
        :type org: str
        :param blockchain: The blockchain.
        :type blockchain: str
        :param address: The account address.
        :type address: str
        :param input_pairs: A list of tuples defining the data type and data to sign.
        :type input_pairs: List[Tuple(str, Any)]

        :Keyword Arguments:
            * **headers** (`Optional[dict]`) - additional http headers
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: a Dict with the signed content.
        :rtype: dict
        """
        payload = {
            "input_pairs": [list(t) for t in input_pairs],
            "hash_message": hash_message,
        }
        return SimbaRequest(
            method="POST",
            endpoint=Path.ORG_ACCOUNT_ADDRESS_SIGN.format(org, blockchain, address),
            login=login,
        ).send_sync(config=config, json_payload=payload, headers=headers or {})

    def subscribe(
        self,
        org: str,
        notification_endpoint: str,
        auth_type: str,
        contract_name: str,
        txn: str,
        subscription_type: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        POST ``/v2/organisations/{organisation}/subscriptions/``

        Subscribe to a method called or an event fired by a contract.

        :param org: The organisation to save to.
        :type org: str
        :param notification_endpoint: The endpoint to send to
        :type notification_endpoint: str
        :param auth_type: The authentication type defined in a notification config
        :type auth_type: str
        :param contract_name: The name of the contract API
        :type contract_name: str
        :param txn: The transaction (Method or Event) in the contract.
        :type txn: str
        :param subscription_type: The type of subscription - METHOD or EVENT
        :type subscription_type: str

        :Keyword Arguments:
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: The subscription object
        :rtype: dict
        """
        inputs = {
            "endpoint": notification_endpoint,
            "txn": txn,
            "contract": contract_name,
            "auth_type": auth_type,
            "subscription_type": subscription_type,
        }
        results = SimbaRequest(
            endpoint=Path.SUBSCRIPTIONS.format(org),
            login=login,
        ).retrieve_sync(config=config)
        for result in results:
            if (
                result.get("endpoint") == notification_endpoint
                and result.get("txn") == txn
                and result.get("contract") == contract_name
                and result.get("auth_type") == auth_type
            ):
                return result
        sub = PostRequest(
            endpoint=Path.SUBSCRIPTIONS.format(org),
            login=login,
        ).post_sync(config=config, json_payload=inputs)
        return sub

    def set_notification_config(
        self,
        org: str,
        scheme: str,
        auth_type: str,
        auth_info: dict,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        POST ``/v2/organisations/{organisation}/notification_config/``

        Set a notification config for an organisation that can be referenced by auth_type in a subscription.

        :param org: The organisation to save to.
        :type org: str
        :param scheme: THe scheme of the notification - currently HTTP(S), MAILTO and SMS are supported.
        :type scheme: str
        :param auth_type: The authentication type defined in a notification config
        :type auth_type: str
        :param auth_info: Scheme specific auth information such as login details.
        :type auth_info: dict

        :Keyword Arguments:
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: The config object
        :rtype: dict
        """
        inputs = {
            "scheme": scheme,
            "auth_type": auth_type,
            "auth_info": auth_info,
        }
        results = SimbaRequest(
            endpoint=Path.NOTIFICATION_CONFIGS.format(org),
            login=login,
        ).retrieve_sync(config=config)
        for result in results:
            if (
                result.get("scheme") == scheme
                and result.get("auth_type") == auth_type
                and result.get("auth_info") == auth_info
            ):
                return result
        conf = PostRequest(
            endpoint=Path.NOTIFICATION_CONFIGS.format(org),
            login=login,
        ).post_sync(config=config, json_payload=inputs)
        return conf

    def wait_for_org_transaction(
        self,
        org: str,
        uid: str,
        total_time: int = 0,
        max_time: int = 40,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        GET ``/v2/organisations/{organisation}/transactions/{txn_id}/``

        Wait for a transaction to complete, i.e., it's state becomes COMPLETED.

        :param org: The organisation to save to.
        :type org: str
        :param uid: The ID of the transaction
        :type uid: str

        :Keyword Arguments:
            * **total_time** (`int`) - total time waited so far. leave this at zero as it gets incremented through
                                        recursive calls.
            * **max_time** (`int`) - maximum seconds ot wait. Default is 40
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: The transaction object
        :rtype: dict
        """
        res = GetRequest(
            endpoint=Path.ORG_TXN.format(org, uid),
            login=login,
        ).get_sync(config=config)
        state = res["state"]
        if state == "FAILED":
            raise ValueError("TXN FAILED: {}".format(res))
        if state == "COMPLETED":
            return res
        else:
            if total_time > max_time:
                raise ValueError("waited way too long")
            time.sleep(2)
            total_time += 2
            return self.wait_for_org_transaction(
                org=org,
                uid=uid,
                total_time=total_time,
                max_time=max_time,
                login=login,
                config=config,
            )

    def add_event_name(
        self,
        event_name: Optional[str] = None,
        query_args: Optional[SearchFilter] = None,
    ) -> Optional[SearchFilter]:
        if event_name:
            if not query_args:
                query_args = SearchFilter()
            if not query_args.has_filter_value(
                field="event_name", op=FilterOp.EQ, value=event_name
            ):
                query_args.add_filter(
                    FieldFilter(op=FilterOp.EQ, field="event_name", value=event_name)
                )
        return query_args

    def create_secret(
        self,
        name: str,
        headers: Optional[dict] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        POST ``/user/api_applications/``

        create a user secret.

        :param name: The secret name.
        :type name: str

        :Keyword Arguments:
            * **headers** (`Optional[dict]`) - additional http headers
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: a client secret
        :rtype: dict
        """
        payload = {
            "name": name,
        }
        return SimbaRequest(
            method="POST",
            endpoint=Path.USER_SECRET,
            login=login,
        ).send_sync(config=config, json_payload=payload, headers=headers or {})

    def get_secrets(
        self,
        headers: Optional[dict] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> List[dict]:
        """
        GET ``/user/api_applications/``

        Get user secrets.

        :Keyword Arguments:
            * **headers** (`Optional[dict]`) - additional http headers
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: client secrets
        :rtype: list
        """
        return SimbaRequest(
            method="POST",
            endpoint=Path.USER_SECRET,
            login=login,
        ).retrieve_sync(config=config, headers=headers or {})

    def admin_set_delegate(
        self,
        user: str,
        delegate: bool,
        headers: Optional[dict] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        POST ``/admin/users/{user}/delegate/``

        Set the user as delegate.

        :param user: The user ID.
        :type user: str
        :param delegate: To delegate or not.
        :type delegate: bool

        :Keyword Arguments:
            * **headers** (`Optional[dict]`) - additional http headers
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: a delegate setting.
        :rtype: dict
        """
        payload = {
            "delegate": delegate,
        }
        return SimbaRequest(
            method="POST",
            endpoint=Path.ADMIN_DELEGATE.create(user),
            login=login,
        ).send_sync(config=config, json_payload=payload, headers=headers or {})

    def admin_create_account(
        self,
        network: str,
        alias: str,
        owner: str,
        owner_type: str,
        headers: Optional[dict] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        POST ``/admin/accounts/``

        Create a new account for a user.

        :param network: The blockchain name.
        :type network: str
        :param alias: The account alias.
        :type alias: str
        :param owner: The account owner.
        :type owner: str
        :param owner_type: The account owner type. One of User or Organisation.
        :type owner_type: str

        :Keyword Arguments:
            * **headers** (`Optional[dict]`) - additional http headers
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: an account object.
        :rtype: dict
        """

        payload = {
            "network": network,
            "nickname": alias,
            "alias": alias,
            "owner": {"type": owner_type, "identifier": owner},
        }
        return SimbaRequest(
            method="POST",
            endpoint=Path.ADMIN_ACCOUNTS,
            login=login,
        ).send_sync(config=config, json_payload=payload, headers=headers or {})

    def admin_account_sign(
        self,
        network: str,
        alias: str,
        owner_identifier: str,
        owner_type: str,
        input_pairs: List[Tuple[str, Any]],
        hash_message: Optional[bool] = False,
        user_identifier: Optional[str] = None,
        user_type: Optional[str] = None,
        headers: Optional[dict] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        POST ``/admin/blockchain/{name}/sign/``

        Sign on behalf of a user.

        :param network: The blockchain name.
        :type network: str
        :param alias: The account alias.
        :type alias: str
        :param owner_identifier: The account owner.
        :type owner_identifier: str
        :param owner_type: The account owner type. One of User or Organisation.
        :type owner_type: str
        :param user_identifier: The requesting user.
        :type user_identifier: str
        :param user_type: The requesting user type. One of User or SimbaIdentity. Required if owner is an organisation.
        :type user_type: Optional[str]
        :param input_pairs: A list of tuples defining the data type and data to sign.
        :type input_pairs: List[Tuple(str, Any)]
        :param hash_message: Whether to hash the message before signing or not
        :type hash_message: Optional[bool]. Default False

        :Keyword Arguments:
            * **headers** (`Optional[dict]`) - additional http headers
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: a signed data structure.
        :rtype: dict
        """
        if owner_type == "Organisation" and (not user_identifier or not user_type):
            raise ValueError("Owner is an org but user or user type is not given.")
        payload = {
            "account": {
                "identifier": {
                    "type": "Alias",
                    "value": alias
                },
                "owner": {
                    "type": owner_type,
                    "identifier": owner_identifier
                }
            },
            "data": {
                "input_pairs": [list(t) for t in input_pairs],
                "hash_message": hash_message,
            }
        }
        if owner_type == "Organisation":
            payload["account"]["user"] = {
                    "type": user_type,
                    "identifier": user_identifier
                }
        return SimbaRequest(
            method="POST",
            endpoint=Path.ADMIN_BLOCKCHAIN_SIGN.create(network),
            login=login,
        ).send_sync(config=config, json_payload=payload, headers=headers or {})

    def admin_account_validate(
        self,
        network: str,
        alias: str,
        owner_identifier: str,
        owner_type: str,
        user_identifier: Optional[str] = None,
        user_type: Optional[str] = None,
        headers: Optional[dict] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        """
        POST ``/admin/blockchain/{name}/validate/``

        Validate the user has access to the given wallet.

        :param network: The blockchain name.
        :type network: str
        :param alias: The account alias.
        :type alias: str
        :param owner_identifier: The account owner.
        :type owner_identifier: str
        :param owner_type: The account owner type. One of User or Organisation.
        :type owner_type: str
        :param user_identifier: The requesting user.
        :type user_identifier: str
        :param user_type: The requesting user type. One of User or SimbaIdentity. Required if owner is an organisation.
        :type user_type: Optional[str]

        :Keyword Arguments:
            * **headers** (`Optional[dict]`) - additional http headers
            * **login** (`Optional[Login]`)
            * **config** (`Optional[ConnectionConfig]`)
        :return: a signed data structure.
        :rtype: dict
        """
        if owner_type == "Organisation" and (not user_identifier or not user_type):
            raise ValueError("Owner is an org but user or user type is not given.")
        payload = {
            "account": {
                "identifier": {
                    "type": "Alias",
                    "value": alias
                },
                "owner": {
                    "type": owner_type,
                    "identifier": owner_identifier
                }
            }
        }
        if owner_type == "Organisation":
            payload["account"]["user"] = {
                    "type": user_type,
                    "identifier": user_identifier
                }
        return SimbaRequest(
            method="POST",
            endpoint=Path.ADMIN_BLOCKCHAIN_VALIDATE.create(network),
            login=login,
        ).send_sync(config=config, json_payload=payload, headers=headers or {})


