import base64
import logging
import time

from typing import AsyncGenerator, List, Optional, Tuple, Union

from libsimba.schemas import (
    ConnectionConfig,
    FileDict,
    Login,
    MethodCallArgs,
    SearchFilter,
    TxnHeaders,
)
from libsimba.simba_contract import SimbaContract
from libsimba.simba_request import GetRequest, PostRequest, PutRequest, SimbaRequest
from libsimba.simba_sync import SimbaSync
from libsimba.utils import Path, get_address, get_deployed_artifact_id


logger = logging.getLogger(__name__)


class Simba():
    def __init__(self, *args, **kwargs):
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
        return await GetRequest(endpoint=Path.USER_WALLET_SET, login=login).get(
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
        app_id: str,
        query_args: Optional[SearchFilter] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        query_args = query_args or {}
        return await GetRequest(
            endpoint=Path.APP.format(app_id), query_params=query_args, login=login
        ).get(config=config)

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
        event_name: str,
        query_args: Optional[SearchFilter] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> AsyncGenerator[List[dict], None]:
        return SimbaRequest(
            endpoint=Path.CONTRACT_EVENTS.format(app_id, contract_name, event_name),
            query_params=query_args,
            login=login,
        ).retrieve_iter(config=config)

    async def get_events(
        self,
        app_id: str,
        contract_name: str,
        event_name: str,
        query_args: Optional[SearchFilter] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> List[dict]:
        return await SimbaRequest(
            endpoint=Path.CONTRACT_EVENTS.format(app_id, contract_name, event_name),
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
        event_name: str,
        query_args: Optional[SearchFilter] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> List[dict]:
        return await SimbaRequest(
            endpoint=Path.CONTRACT_EVENTS.format(app_id, contract_name, event_name),
            query_params=query_args,
            login=login,
        ).retrieve(config=config)

    async def list_events_by_contract(
        self,
        app_id: str,
        contract_name: str,
        event_name: str,
        query_args: Optional[SearchFilter] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> AsyncGenerator[List[dict], None]:
        return SimbaRequest(
            endpoint=Path.CONTRACT_EVENTS.format(app_id, contract_name, event_name),
            query_params=query_args,
            login=login,
        ).retrieve_iter(config=config)

    async def submit_contract_method(
        self,
        app_id: str,
        contract_name: str,
        method_name: str,
        inputs: Optional[dict],
        files: FileDict = None,
        txn_headers: TxnHeaders = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        headers = txn_headers.as_headers() if txn_headers else {}
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
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        return await GetRequest(
            endpoint=Path.CONTRACT_METHOD.format(app_id, contract_name, method_name),
            login=login,
        ).call(config=config, args=args)

    async def submit_contract_method_sync(
        self,
        app_id: str,
        contract_name: str,
        method_name: str,
        inputs: Optional[dict],
        files: FileDict = None,
        txn_headers: TxnHeaders = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        headers = txn_headers.as_headers() if txn_headers else {}
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
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        return await PostRequest(
            endpoint=Path.APP_TXN.format(app_id, txn_id), login=login
        ).post(json_payload={"transaction": txn}, config=config)

    async def save_design(
        self,
        org: str,
        name: str,
        code: str,
        design_id: Optional[str] = None,
        target_contract: str = None,
        libraries: dict = None,
        encode: bool = True,
        model: str = None,
        binary_targets: List[str] = None,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> dict:
        if encode:
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
            time.sleep(2)
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
        full["singleton"] = True
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
        full["singleton"] = True
        return await PostRequest(
            endpoint=Path.DEPLOYMENTS.format(org),
            login=login,
        ).post(json_payload=full, config=config)

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
            time.sleep(2)
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

    async def get_artifacts(
        self,
        org: str,
        login: Login = None,
        config: ConnectionConfig = None,
    ) -> List[dict]:
        return await SimbaRequest(
            endpoint=Path.CONTRACT_ARTIFACTS.format(org),
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
