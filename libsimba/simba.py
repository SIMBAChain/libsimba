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
import asyncio
import base64
import json
import logging

from typing import Any, AsyncGenerator, List, Optional, Tuple, Union

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
from libsimba.simba_contract import SimbaContract
from libsimba.simba_request import (
    GetRequest,
    PatchRequest,
    PostRequest,
    PutRequest,
    SimbaRequest,
)
from libsimba.simba_sync import SimbaSync
from libsimba.utils import (
    Path,
    get_address,
    get_address_by_name,
    get_deployed_artifact_id,
)


logger = logging.getLogger(__name__)


class Simba(SimbaSync):
    def __init__(self, *args, **kwargs):
        """
        See libsimba Settings for args that can be passed
        :param kwargs: args that can configure Settings if settings
        have not been initialized
        """
        super().__init__(*args, **kwargs)

    def smart_contract_client(self, app_name: str, contract_name: str) -> SimbaContract:
        return SimbaContract(self, app_name, contract_name)

    async def whoami(
        self, login: Login = None, config: ConnectionConfig = None
    ) -> dict:
        return await GetRequest(endpoint=Path.WHOAMI, login=login).get(config=config)

    async def fund(
        self,
        blockchain: str,
        address: str,
        amount: Union[str, int],
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        inputs = {"address": address, "amount": amount}
        return await PostRequest(
            endpoint=Path.USER_FUND_ADDRESS.format(blockchain), login=login
        ).post(config=config, json_payload=inputs)

    async def balance(
        self,
        blockchain: str,
        address: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> Union[str, int]:
        resp = await GetRequest(
            endpoint=Path.USER_ADDRESS_BALANCE.format(blockchain, address), login=login
        ).get(config=config)
        return resp.get("balance")

    async def admin_set_wallet(
        self,
        user_id: str,
        blockchain: str,
        pub: str,
        priv: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        inputs = {"blockchain": blockchain, "identities": [{"pub": pub, "priv": priv}]}
        resp = await PostRequest(
            endpoint=Path.ADMIN_WALLET_SET.format(user_id), login=login
        ).post(config=config, json_payload=inputs)
        return resp

    async def set_wallet(
        self,
        blockchain: str,
        pub: str,
        priv: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        inputs = {"blockchain": blockchain, "identities": [{"pub": pub, "priv": priv}]}
        resp = await PostRequest(endpoint=Path.USER_WALLET_SET, login=login).post(
            config=config, json_payload=inputs
        )
        return resp

    async def get_wallet(
        self, login: Login = None, config: ConnectionConfig = None
    ) -> dict:
        return await GetRequest(endpoint=Path.USER_WALLET, login=login).get(
            config=config
        )

    async def create_org(
        self,
        name: str,
        display: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        req = GetRequest(endpoint=Path.ORGANISATION.format(name), login=login)
        try:
            return await req.get(config=config)
        except Exception as ex:
            if req.status == 404:
                inputs = {"name": name, "display_name": display}
                return await PostRequest(endpoint=Path.ORGANISATIONS, login=login).post(
                    config=config, json_payload=inputs
                )
            else:
                raise ex

    async def create_app(
        self,
        org: str,
        name: str,
        display: str,
        force: bool = False,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        req = GetRequest(endpoint=Path.ORG_APP.format(org, name), login=login)
        try:
            return await req.get(config=config)
        except Exception as ex:
            if req.status == 404:
                inputs = {"name": name, "display_name": display}
                return await PostRequest(
                    endpoint=Path.ORG_APPS.format(org), login=login
                ).post(config=config, json_payload=inputs)
            else:
                raise ex

    async def list_applications(
        self,
        query_args: Optional[SearchFilter] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> AsyncGenerator[List[dict], None]:
        return SimbaRequest(
            endpoint=Path.APPS, query_params=query_args, login=login
        ).retrieve_iter(config=config)

    async def get_applications(
        self,
        query_args: Optional[SearchFilter] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> List[dict]:
        return await SimbaRequest(
            endpoint=Path.APPS, query_params=query_args, login=login
        ).retrieve(config=config)

    async def get_application(
        self,
        org,
        app_id: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        return await GetRequest(endpoint=Path.APP.format(org, app_id), login=login).get(
            config=config
        )

    async def list_application_transactions(
        self,
        app_id: str,
        query_args: Optional[SearchFilter] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> AsyncGenerator[List[dict], None]:
        return SimbaRequest(
            endpoint=Path.APP_TXNS.format(app_id), query_params=query_args, login=login
        ).retrieve_iter(config=config)

    async def get_application_transactions(
        self,
        app_id: str,
        query_args: Optional[SearchFilter] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> List[dict]:
        return await SimbaRequest(
            endpoint=Path.APP_TXNS.format(app_id), query_params=query_args, login=login
        ).retrieve(config=config)

    async def get_application_contract(
        self,
        app_id: str,
        contract_name: str,
        query_args: Optional[SearchFilter] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        return await GetRequest(
            endpoint=Path.APP_CONTRACT.format(app_id, contract_name),
            query_params=query_args,
            login=login,
        ).get(config=config)

    async def list_contract_transactions(
        self,
        app_id: str,
        contract_name: str,
        query_args: Optional[SearchFilter] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> AsyncGenerator[List[dict], None]:
        return SimbaRequest(
            endpoint=Path.CONTRACT_TXNS.format(app_id, contract_name),
            query_params=query_args,
            login=login,
        ).retrieve_iter(config=config)

    async def get_contract_transactions(
        self,
        app_id: str,
        contract_name: str,
        query_args: Optional[SearchFilter] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> List[dict]:
        return await SimbaRequest(
            endpoint=Path.CONTRACT_TXNS.format(app_id, contract_name),
            query_params=query_args,
            login=login,
        ).retrieve(config=config)

    async def list_contracts(
        self,
        app_id: str,
        query_args: Optional[SearchFilter] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> AsyncGenerator[List[dict], None]:
        return SimbaRequest(
            endpoint=Path.APP_CONTRACTS.format(app_id),
            query_params=query_args,
            login=login,
        ).retrieve_iter(config=config)

    async def get_contracts(
        self,
        app_id: str,
        query_args: Optional[SearchFilter] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> List[dict]:
        return await SimbaRequest(
            endpoint=Path.APP_CONTRACTS.format(app_id),
            query_params=query_args,
            login=login,
        ).retrieve(config=config)

    async def validate_bundle(
        self,
        app_id: str,
        contract_name: str,
        bundle_hash: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        return await GetRequest(
            endpoint=Path.VALIDATE_BUNDLE.format(app_id, contract_name, bundle_hash),
            login=login,
        ).get(config=config)

    async def get_bundle(
        self,
        app_id: str,
        contract_name: str,
        bundle_hash: str,
        download_location: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> None:
        return await SimbaRequest(
            endpoint=Path.BUNDLE.format(app_id, contract_name, bundle_hash), login=login
        ).download(location=download_location, config=config)

    async def get_bundle_file(
        self,
        app_id: str,
        contract_name: str,
        bundle_hash: str,
        file_name,
        download_location: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ):
        return await SimbaRequest(
            endpoint=Path.BUNDLE_FILE.format(
                app_id, contract_name, bundle_hash, file_name
            ),
            login=login,
        ).download(location=download_location, config=config)

    async def get_manifest_for_bundle_from_bundle_hash(
        self,
        app_id: str,
        contract_name: str,
        bundle_hash: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        return await GetRequest(
            endpoint=Path.BUNDLE_MANIFEST.format(app_id, contract_name, bundle_hash),
            login=login,
        ).get(config=config)

    async def get_contract_info(
        self,
        app_id: str,
        contract_name: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        return await GetRequest(
            endpoint=Path.CONTRACT_INFO.format(app_id, contract_name), login=login
        ).get(config=config)

    async def list_events(
        self,
        app_id: str,
        contract_name: str,
        event_name: Optional[str] = None,
        query_args: Optional[SearchFilter] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> AsyncGenerator[List[dict], None]:
        query_args = self.add_event_name(event_name=event_name, query_args=query_args)
        return SimbaRequest(
            endpoint=Path.CONTRACT_EVENTS.format(app_id, contract_name),
            query_params=query_args,
            login=login,
        ).retrieve_iter(config=config)

    async def get_events(
        self,
        app_id: str,
        contract_name: str,
        event_name: Optional[str] = None,
        query_args: Optional[SearchFilter] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> List[dict]:
        query_args = self.add_event_name(event_name=event_name, query_args=query_args)
        return await SimbaRequest(
            endpoint=Path.CONTRACT_EVENTS.format(app_id, contract_name),
            query_params=query_args,
            login=login,
        ).retrieve(config=config)

    async def get_receipt(
        self,
        app_id: str,
        contract_name: str,
        receipt_hash: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        return await GetRequest(
            endpoint=Path.CONTRACT_RECEIPT.format(app_id, contract_name, receipt_hash),
            login=login,
        ).get(config=config)

    async def get_transaction(
        self,
        app_id: str,
        contract_name: str,
        transaction_hash: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        return await GetRequest(
            endpoint=Path.CONTRACT_TXN.format(app_id, contract_name, transaction_hash),
            login=login,
        ).get(config=config)

    async def get_transaction_by_id(
        self,
        org_name: str,
        transaction_id: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        return await GetRequest(
            endpoint=Path.ORG_TXN.format(org_name, transaction_id),
            login=login,
        ).get(config=config)
        
    async def get_transactions_by_method(
        self,
        app_id: str,
        contract_name: str,
        method_name: str,
        query_args: Optional[SearchFilter] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> List[dict]:
        return await SimbaRequest(
            endpoint=Path.CONTRACT_METHOD.format(app_id, contract_name, method_name),
            query_params=query_args,
            login=login,
        ).retrieve(config=config)

    async def list_transactions_by_method(
        self,
        app_id: str,
        contract_name: str,
        method_name: str,
        query_args: Optional[SearchFilter] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> AsyncGenerator[List[dict], None]:
        return SimbaRequest(
            endpoint=Path.CONTRACT_METHOD.format(app_id, contract_name, method_name),
            query_params=query_args,
            login=login,
        ).retrieve_iter(config=config)

    async def get_transactions_by_contract(
        self,
        app_id: str,
        contract_name: str,
        query_args: Optional[SearchFilter] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> List[dict]:
        return await SimbaRequest(
            endpoint=Path.CONTRACT_TXNS.format(app_id, contract_name),
            query_params=query_args,
            login=login,
        ).retrieve(config=config)

    async def list_transactions_by_contract(
        self,
        app_id: str,
        contract_name: str,
        query_args: Optional[SearchFilter] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> AsyncGenerator[List[dict], None]:
        return SimbaRequest(
            endpoint=Path.CONTRACT_TXNS.format(app_id, contract_name),
            query_params=query_args,
            login=login,
        ).retrieve_iter(config=config)

    async def get_events_by_contract(
        self,
        app_id: str,
        contract_name: str,
        event_name: Optional[str] = None,
        query_args: Optional[SearchFilter] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> List[dict]:
        query_args = self.add_event_name(event_name=event_name, query_args=query_args)
        return await SimbaRequest(
            endpoint=Path.CONTRACT_EVENTS.format(app_id, contract_name),
            query_params=query_args,
            login=login,
        ).retrieve(config=config)

    async def list_events_by_contract(
        self,
        app_id: str,
        contract_name: str,
        event_name: Optional[str] = None,
        query_args: Optional[SearchFilter] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> AsyncGenerator[List[dict], None]:
        query_args = self.add_event_name(event_name=event_name, query_args=query_args)
        return SimbaRequest(
            endpoint=Path.CONTRACT_EVENTS.format(app_id, contract_name),
            query_params=query_args,
            login=login,
        ).retrieve_iter(config=config)

    async def submit_contract_method(
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
        headers = headers or {}
        headers.update(txn_headers.as_headers() if txn_headers else {})
        inputs = inputs if inputs else {}
        result = await PostRequest(
            endpoint=Path.CONTRACT_METHOD.format(app_id, contract_name, method_name),
            login=login,
        ).post(json_payload=inputs, files=files, headers=headers, config=config)
        return result

    async def call_contract_method(
        self,
        app_id: str,
        contract_name: str,
        method_name: str,
        args: Optional[MethodCallArgs] = None,
        headers: Optional[dict] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        return await GetRequest(
            endpoint=Path.CONTRACT_METHOD.format(app_id, contract_name, method_name),
            login=login,
        ).call(config=config, args=args, headers=headers or {})

    async def submit_contract_method_sync(
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
        headers = headers or {}
        headers.update(txn_headers.as_headers() if txn_headers else {})
        inputs = inputs if inputs else {}
        result = await PostRequest(
            endpoint=Path.SYNC_CONTRACT_METHOD.format(
                app_id, contract_name, method_name
            ),
            login=login,
        ).post(json_payload=inputs, files=files, headers=headers, config=config)
        return result

    # TODO(Adam): Make a transaction object to assist the user. Right now it's just a dict
    async def submit_signed_transaction(
        self,
        app_id: str,
        txn_id: str,
        txn: dict,
        headers: Optional[dict] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        return await PatchRequest(
            endpoint=Path.APP_TXN.format(app_id, txn_id), login=login
        ).patch(json_payload={"transaction": txn}, config=config, headers=headers or {})

    async def save_design(
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
        if config.timeout < 120:
            config.timeout = 120
        if design_id:
            return await PutRequest(
                endpoint=Path.DESIGN.format(org, design_id), login=login
            ).put(json_payload=full, config=config)
        else:
            return await PostRequest(
                endpoint=Path.DESIGNS.format(org), login=login
            ).post(json_payload=full, config=config)

    async def wait_for_deployment(
        self,
        org: str,
        uid: str,
        total_time: int = 0,
        max_time: int = 480,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        res = await SimbaRequest(
            endpoint=Path.DEPLOYMENT.format(org, uid), method="GET", login=login
        ).send(config=config)
        state = res["state"]
        if state == "COMPLETED":
            return res
        else:
            if total_time > max_time:
                raise ValueError("[wait_for_deployment] :: waited way too long")
            await asyncio.sleep(2)
            total_time += 2
            return await self.wait_for_deployment(
                org, uid, total_time=total_time, login=login, config=config
            )

    async def deploy_design(
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

        full = {"blockchain": blockchain, "storage": storage, "api_name": api_name}
        if display_name:
            full["display_name"] = display_name
        full["app_name"] = app
        if args:
            full["args"] = args
        return await PostRequest(
            endpoint=Path.DESIGN_DEPLOY.format(org, design_id),
            login=login,
        ).post(json_payload=full, config=config)

    async def deploy_artifact(
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
        return await PostRequest(
            endpoint=Path.DEPLOYMENTS.format(org),
            login=login,
        ).post(json_payload=full, config=config)

    async def deploy_library(
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
        return await PostRequest(
            endpoint=Path.LIBRARIES.create(org),
            login=login,
        ).post(json_payload=full, config=config)

    async def wait_for_deploy_library(
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

        res = await self.deploy_library(
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
            deployed = await self.wait_for_deployment(org, deployment_id)
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

    async def wait_for_deploy_design(
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

        res = await self.deploy_design(
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
            deployed = await self.wait_for_deployment(org, deployment_id)
            address = get_address(deployed)
            contract_id = get_deployed_artifact_id(deployed)
        except Exception as ex:
            logger.warning("[deploy] :: failed to wait for deployment: {}".format(ex))
            address = None
            contract_id = None
        return address, contract_id

    async def wait_for_deploy_artifact(
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

        res = await self.deploy_artifact(
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
            deployed = await self.wait_for_deployment(org, deployment_id)
            address = get_address(deployed)
            contract_id = get_deployed_artifact_id(deployed)
        except Exception as ex:
            logger.warning("[deploy] :: failed to wait for deployment: {}".format(ex))
            address = None
            contract_id = None
        return address, contract_id

    async def wait_for_org_transaction(
        self,
        org: str,
        uid: str,
        total_time: int = 0,
        max_time: int = 40,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        res = await GetRequest(
            endpoint=Path.ORG_TXN.format(org, uid),
            login=login,
        ).get(config=config)
        state = res["state"]
        if state == "FAILED":
            raise ValueError("TXN FAILED: {}".format(res))
        if state == "COMPLETED":
            return res
        else:
            if total_time > max_time:
                raise ValueError("waited way too long")
            await asyncio.sleep(2)
            total_time += 2
            return await self.wait_for_org_transaction(
                org=org,
                uid=uid,
                total_time=total_time,
                max_time=max_time,
                login=login,
                config=config,
            )

    async def get_designs(
        self,
        org: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> List[dict]:
        return await SimbaRequest(
            endpoint=Path.DESIGNS.format(org),
            login=login,
        ).retrieve(config=config)

    async def get_blockchains(
        self,
        org: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> List[dict]:
        return await SimbaRequest(
            endpoint=Path.BLOCKCHAINS.format(org),
            login=login,
        ).retrieve(config=config)

    async def get_storage(
        self,
        org: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> List[dict]:
        return await SimbaRequest(
            endpoint=Path.STORAGES.format(org),
            login=login,
        ).retrieve(config=config)

    async def get_abi(
        self,
        blockchain: str,
        contract_address: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        return await SimbaRequest(
            endpoint=Path.CONTRACT_ABI.create(blockchain, contract_address),
            login=login,
        ).send(config=config)

    async def get_accounts(
        self,
        nickname: Optional[str] = None,
        alias: Optional[str] = None,
        network: Optional[str] = None,
        headers: Optional[dict] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> List[dict]:
        params = None
        if nickname or alias:
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
        return await SimbaRequest(
            endpoint=Path.USER_ACCOUNTS,
            query_params=params,
            login=login,
        ).retrieve(config=config, headers=headers or {})

    async def get_account(
        self,
        uid: str,
        headers: Optional[dict] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        return await SimbaRequest(
            endpoint=Path.USER_ACCOUNT.format(uid),
            login=login,
        ).send(config=config, headers=headers or {})

    async def create_account(
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
        payload = {
            "network_type": network_type,
            "network_subtype": network_subtype,
            "network": network,
            "nickname": nickname,
            "alias": alias,
        }
        return await SimbaRequest(
            method="POST",
            endpoint=Path.USER_ACCOUNTS,
            login=login,
        ).send(config=config, json_payload=payload, headers=headers or {})

    async def set_account(
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
        payload = {
            "network_type": network_type,
            "network_subtype": network_subtype,
            "network": network,
            "nickname": nickname,
            "alias": alias,
            "public_key": address,
            "private_key": private_key,
        }
        return await SimbaRequest(
            method="POST",
            endpoint=Path.USER_ACCOUNT_SET,
            login=login,
        ).send(config=config, json_payload=payload, headers=headers or {})

    async def account_sign(
        self,
        uid: str,
        input_pairs: List[Tuple[str, Any]],
        hash_message: Optional[bool] = False,
        headers: Optional[dict] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        payload = {
            "input_pairs": [list(t) for t in input_pairs],
            "hash_message": hash_message,
        }
        return await SimbaRequest(
            method="POST",
            endpoint=Path.USER_ACCOUNT_SIGN.format(uid),
            login=login,
        ).send(config=config, json_payload=payload)

    async def account_address_sign(
        self,
        blockchain: str,
        address: str,
        input_pairs: List[Tuple[str, Any]],
        hash_message: Optional[bool] = False,
        headers: Optional[dict] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        payload = {
            "input_pairs": [list(t) for t in input_pairs],
            "hash_message": hash_message,
        }
        return await SimbaRequest(
            method="POST",
            endpoint=Path.USER_ACCOUNT_ADDRESS_SIGN.create(blockchain, address),
            login=login,
        ).send(config=config, json_payload=payload)

    async def admin_get_accounts(
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
        GET ``/v2/organisations/{org}/accounts/``

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
        return await SimbaRequest(
            endpoint=Path.ADMIN_ACCOUNTS,
            query_params=params.query,
            login=login,
        ).retrieve(config=config, headers=headers or {})

    async def get_org_accounts(
        self,
        org: str,
        nickname: Optional[str] = None,
        alias: Optional[str] = None,
        network: Optional[str] = None,
        headers: Optional[dict] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> List[dict]:
        params = None
        if nickname or alias:
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
        return await SimbaRequest(
            endpoint=Path.ORG_ACCOUNTS.create(org),
            query_params=params,
            login=login,
        ).retrieve(config=config, headers=headers or {})

    async def get_org_account(
        self,
        org: str,
        uid: str,
        headers: Optional[dict] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        return await SimbaRequest(
            endpoint=Path.ORG_ACCOUNT.create(org, uid),
            login=login,
        ).send(config=config, headers=headers or {})

    async def create_org_account(
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
        payload = {
            "network_type": network_type,
            "network_subtype": network_subtype,
            "network": network,
            "nickname": nickname,
            "alias": alias,
        }
        return await SimbaRequest(
            method="POST",
            endpoint=Path.ORG_ACCOUNTS.create(org),
            login=login,
        ).send(config=config, json_payload=payload, headers=headers or {})

    async def set_org_account(
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
        payload = {
            "network_type": network_type,
            "network_subtype": network_subtype,
            "network": network,
            "nickname": nickname,
            "alias": alias,
            "public_key": address,
            "private_key": private_key,
        }
        return await SimbaRequest(
            method="POST",
            endpoint=Path.ORG_ACCOUNT_SET.create(org),
            login=login,
        ).send(config=config, json_payload=payload, headers=headers or {})

    async def org_account_sign(
        self,
        org: str,
        uid: str,
        input_pairs: List[Tuple[str, Any]],
        hash_message: Optional[bool] = False,
        headers: Optional[dict] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        payload = {
            "input_pairs": [list(t) for t in input_pairs],
            "hash_message": hash_message,
        }
        return await SimbaRequest(
            method="POST",
            endpoint=Path.ORG_ACCOUNT_SIGN.create(org, uid),
            login=login,
        ).send(config=config, json_payload=payload)

    async def org_account_address_sign(
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
        payload = {
            "input_pairs": [list(t) for t in input_pairs],
            "hash_message": hash_message,
        }
        return await SimbaRequest(
            method="POST",
            endpoint=Path.ORG_ACCOUNT_ADDRESS_SIGN.create(org, blockchain, address),
            login=login,
        ).send(config=config, json_payload=payload)

    async def get_artifacts(
        self,
        org: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> List[dict]:
        return await SimbaRequest(
            endpoint=Path.CONTRACT_ARTIFACTS.create(org),
            login=login,
        ).retrieve(config=config)

    async def get_artifact(
        self,
        org: str,
        artifact_id: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        return await GetRequest(
            endpoint=Path.CONTRACT_ARTIFACT.format(org, artifact_id),
            login=login,
        ).get(config=config)

    async def create_artifact(
        self,
        org: str,
        design_id: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        inputs = {"design_id": design_id}
        return await PostRequest(
            endpoint=Path.CONTRACT_ARTIFACTS.format(org),
            login=login,
        ).post(config=config, json_payload=inputs)

    async def subscribe(
        self,
        org: str,
        notification_endpoint: str,
        auth_type: str,
        contract_api: str,
        txn: str,
        subscription_type: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        inputs = {
            "endpoint": notification_endpoint,
            "txn": txn,
            "contract": contract_api,
            "auth_type": auth_type,
            "subscription_type": subscription_type,
        }
        results = await SimbaRequest(
            endpoint=Path.SUBSCRIPTIONS.format(org),
            login=login,
        ).retrieve(config=config)
        for result in results:
            if (
                result.get("endpoint") == notification_endpoint
                and result.get("txn") == txn
                and result.get("contract") == contract_api
                and result.get("auth_type") == auth_type
            ):
                return result
        sub = await PostRequest(
            endpoint=Path.SUBSCRIPTIONS.format(org),
            login=login,
        ).post(config=config, json_payload=inputs)
        return sub

    async def set_notification_config(
        self,
        org: str,
        scheme: str,
        auth_type: str,
        auth_info: dict,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        inputs = {
            "scheme": scheme,
            "auth_type": auth_type,
            "auth_info": auth_info,
        }
        results = await SimbaRequest(
            endpoint=Path.NOTIFICATION_CONFIGS.format(org),
            login=login,
        ).retrieve(config=config)
        for result in results:
            if (
                result.get("scheme") == scheme
                and result.get("auth_type") == auth_type
                and result.get("auth_info") == auth_info
            ):
                return result
        conf = await PostRequest(
            endpoint=Path.NOTIFICATION_CONFIGS.format(org),
            login=login,
        ).post(config=config, json_payload=inputs)
        return conf

    async def create_secret(
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
        return await SimbaRequest(
            method="POST",
            endpoint=Path.USER_SECRET,
            login=login,
        ).send(config=config, json_payload=payload, headers=headers or {})

    async def get_secrets(
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
        return await SimbaRequest(
            method="POST",
            endpoint=Path.USER_SECRET,
            login=login,
        ).retrieve(config=config, headers=headers or {})

    async def admin_set_delegate(
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
        return await SimbaRequest(
            method="POST",
            endpoint=Path.ADMIN_DELEGATE.create(user),
            login=login,
        ).send(config=config, json_payload=payload, headers=headers or {})

    async def admin_create_account(
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
        return await SimbaRequest(
            method="POST",
            endpoint=Path.ADMIN_ACCOUNTS,
            login=login,
        ).send(config=config, json_payload=payload, headers=headers or {})

    async def admin_account_sign(
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
        return await SimbaRequest(
            method="POST",
            endpoint=Path.ADMIN_BLOCKCHAIN_SIGN.create(network),
            login=login,
        ).send(config=config, json_payload=payload, headers=headers or {})

    async def admin_account_validate(
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
        return await SimbaRequest(
            method="POST",
            endpoint=Path.ADMIN_BLOCKCHAIN_VALIDATE.create(network),
            login=login,
        ).send(config=config, json_payload=payload, headers=headers or {})
