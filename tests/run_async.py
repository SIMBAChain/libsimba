import os
from libsimba import Simba, SearchFilter, FieldFilter, FilterOp, MethodCallArgs
from typing import Tuple, List
from tests.run_sync import Runner


class AsyncRunner(Runner):
    async def run(self):
        simba = Simba()
        print("================ checking me ================")
        try:
            await self.me(simba)
        except Exception:
            self.capture_error()
        print("================ checking blockchains ================")
        try:
            chains = await self.blockchains(simba)
            assert self.blockchain_name in chains
        except Exception:
            self.capture_error()
        print("================ checking storage ================")
        try:
            offchains = await self.storage(simba)
            assert self.storage_name in offchains
        except Exception:
            self.capture_error()
        print("================ checking accounts ================")
        try:
            accounts = await self.accounts(simba)
        except Exception:
            self.capture_error()
        try:
            await self.org_app(simba)
            print("================ checking designs ================")
            design_name, design_id = await self.designs(simba)
            print(f"Saved design: {design_name} with id: {design_id}")
        except Exception:
            self.capture_error()
            raise ValueError(self.get_errors())

        print("================ checking deploy ================")
        try:
            app, api_name, address, contract_id = await self.artifacts(
                simba=simba,
                design_id=design_id,
                app=self.name,
                api_name=self.name,
                blockchain=self.blockchain_name,
                storage=self.storage_name,
            )
            print(f"Deployed contract: {address} with id: {contract_id}")

            print("================ checking transactions ================")
            txn_data = await self.contract(
                simba=simba, app=app, org=self.org, api_name=api_name
            )
            bundle_hash = txn_data.get("inputs", {}).get("_bundleHash")
            print("================ checking bundles ================")
            manifest = await self.files(
                simba=simba, app=app, api_name=api_name, bundle_hash=bundle_hash
            )
            print(manifest)
            print("================ checking query ================")
            await self.query(simba=simba, app=app, api_name=api_name)
            print("================ checking getter ================")
            event_list = await self.event_and_getter(
                simba=simba, app=app, api_name=api_name
            )
            print("================ checking contract client ================")
            await self.contract_client(
                simba=simba,
                app=app,
                api_name=api_name,
                bundle_hash=bundle_hash,
                getter_args=event_list[0],
            )
        except Exception:
            self.capture_error()
            raise ValueError(self.get_errors())
        if self.get_errors():
            print("================ errors found ================")
            raise ValueError(self.get_errors())

    async def me(self, simba: Simba):
        me = await simba.whoami()
        print(me)
        self.templates.assert_structure("user", me)

    async def blockchains(self, simba: Simba) -> List[str]:
        blockchains = await simba.get_blockchains(org=self.org)
        print(blockchains)
        self.templates.assert_structure("blockchain", blockchains, many=True)
        return self.get_fields(blockchains)

    async def storage(self, simba: Simba) -> List[str]:
        storage = await simba.get_storage(org=self.org)
        print(storage)
        self.templates.assert_structure("storage", storage, many=True)
        return self.get_fields(storage)

    async def accounts(self, simba: Simba) -> List[str]:
        accounts = await simba.get_accounts()
        print(accounts)
        self.templates.assert_structure("account", accounts, many=True)
        if len(accounts) > 0:
            uid = accounts[0].get("id")
            account = await simba.get_account(uid=uid)
            self.templates.assert_structure("account", account)
            inputs = [("string", "hello"), ("uint256", 10)]
            sig = await simba.account_sign(uid=uid, input_pairs=inputs, hash_message=True)
            self.templates.assert_structure("signature", sig)
        return self.get_fields(accounts)

    async def org_app(self, simba: Simba):
        org_data = await simba.create_org(name=self.org, display="Libsimba")
        print(org_data)
        self.templates.assert_structure("organisation", org_data)
        app_data = await simba.create_app(
            org=self.org, name=self.name, display=self.display
        )
        print(app_data)
        self.templates.assert_structure("application", app_data)
        self.templates.assert_value(type_name="application", data=app_data, value=self.name, path="name")

    async def designs(self, simba: Simba) -> Tuple[str, str]:
        designs = await simba.get_designs(org=self.org)
        self.templates.assert_structure("contract_design", designs, many=True, action="list")

        contract = os.path.join(os.path.dirname(__file__), "data", "TestContract.sol")
        intfce = os.path.join(os.path.dirname(__file__), "data", "Dev.sol")

        lib = os.path.join(os.path.dirname(__file__), "data", "PoseidonT4.sol")
        with open(lib, "r") as sol:
            lib_code = sol.read()
        lib_address, lib_id = await simba.wait_for_deploy_library(
            org=self.org,
            lib_name="PoseidonT4",
            blockchain=self.blockchain_name,
            code=lib_code,
        )
        with open(contract, "r") as sol:
            cont = sol.read()
        with open(intfce, "r") as sol:
            interface = sol.read()
        saved_data = await simba.save_design(
            org=self.org,
            name=self.name,
            code={"TestContract": cont, "Dev": interface, "PoseidonT4": lib_code},
            target_contract="TestContract",
            binary_targets=["TestContract"],
            libraries={"PoseidonT4": lib_address}
        )
        self.templates.assert_structure("contract_design", saved_data)
        return saved_data.get("name"), saved_data.get("id")

    async def artifacts(
        self,
        simba: Simba,
        design_id: str,
        app: str,
        api_name: str,
        storage: str,
        blockchain: str,
    ) -> Tuple[str, str, str, str]:
        artifacts = await simba.get_artifacts(org=self.org)
        self.templates.assert_structure("contract_artifact", artifacts, many=True)
        artifact_data = await simba.create_artifact(org=self.org, design_id=design_id)
        address, contract_id = await simba.wait_for_deploy_artifact(
            org=self.org,
            app=app,
            api_name=api_name,
            artifact_id=artifact_data["id"],
            storage=storage,
            blockchain=blockchain,
        )
        abi = await simba.get_abi(blockchain=blockchain, contract_address=address)
        print(abi.get("abi"))
        print(abi.get("metadata"))
        return app, api_name, address, contract_id

    async def contract(self, simba: Simba, org: str, app: str, api_name: str) -> dict:
        inputs, files = self.bundle_inputs()

        txn = await simba.submit_contract_method(
            app_id=app,
            contract_name=api_name,
            method_name=self.bundle_function(),
            inputs=inputs,
            files=files,
        )
        completed_with_bundle = await simba.wait_for_org_transaction(
            org=org, uid=txn.get("id")
        )
        print(completed_with_bundle)
        self.templates.assert_structure("transaction", completed_with_bundle)

        txn = None
        input_list = self.query_inputs()
        for input in input_list:
            txn = await simba.submit_contract_method(
                app_id=app,
                contract_name=api_name,
                method_name=self.query_function(),
                inputs=input,
            )
        done = await simba.wait_for_org_transaction(org=org, uid=txn.get("id"))
        print(done)
        return completed_with_bundle

    async def query(self, simba: Simba, app: str, api_name: str):
        query = SearchFilter(
            filters=[
                FieldFilter(field="inputs.person.age", op=FilterOp.GT, value=2),
            ],
            fields=["state", "transaction_hash", "inputs"],
            limit=2,
            offset=0,
        )
        gen = await simba.list_transactions_by_method(
            app_id=app,
            contract_name=api_name,
            method_name=self.query_function(),
            query_args=query,
        )
        async for result in gen:
            print(result)
            assert len(result) == 2 or len(result) == 1

    async def files(
        self, simba: Simba, app: str, api_name: str, bundle_hash: str
    ) -> dict:
        manifest = await simba.get_manifest_for_bundle_from_bundle_hash(
            app_id=app, contract_name=api_name, bundle_hash=bundle_hash
        )
        self.templates.assert_structure("manifest", manifest)
        data_dir, zip_path, file_path = self.file_paths()
        await simba.get_bundle(
            app_id=app,
            contract_name=api_name,
            bundle_hash=bundle_hash,
            download_location=zip_path,
        )
        await simba.get_bundle_file(
            app_id=app,
            contract_name=api_name,
            bundle_hash=bundle_hash,
            file_name=self.test_file_name(),
            download_location=file_path,
        )
        self.check_files(data_dir=data_dir, zip_path=zip_path, file_path=file_path)

        return manifest

    async def event_and_getter(
        self, simba: Simba, app: str, api_name: str
    ) -> List[dict]:
        call_inputs = self.call_inputs_again()
        txn = None
        for input in call_inputs:
            txn = await simba.submit_contract_method(
                app_id=app,
                contract_name=api_name,
                method_name=self.event_function(),
                inputs=input,
            )
        done = await simba.wait_for_org_transaction(org=self.org, uid=txn.get("id"))
        print(done)
        events = await simba.get_events(
            app_id=app, contract_name=api_name, event_name=self.event_name()
        )
        event_inputs = []
        for event in events:
            self.templates.assert_structure("event", event)
            event_input = event.get("inputs")
            event_inputs.append(self.getter_args(event_input))
            getter_result = await simba.call_contract_method(
                app_id=app,
                contract_name=api_name,
                method_name=self.call_function(),
                args=MethodCallArgs(args=self.getter_args(event_input)),
            )
            self.templates.assert_structure("getter", getter_result)
        return event_inputs

    async def contract_client(
        self, simba: Simba, app: str, api_name: str, bundle_hash: str, getter_args: dict
    ):
        client = simba.smart_contract_client(app_name=app, contract_name=api_name)
        md = client.get_metadata()
        self.templates.assert_structure("metadata", md)
        query = SearchFilter(
            filters=[
                FieldFilter(field="inputs.person.age", op=FilterOp.GT, value=2),
            ],
            fields=["state", "transaction_hash", "inputs"],
            limit=1000,
            offset=0,
        )
        txns = await client.get_method_transactions(
            query_args=query, method_name=self.query_function()
        )
        self.templates.assert_structure("transaction_fields", txns, many=True)
        getter_response = await client.call_method(
            method_name=self.call_function(), args=MethodCallArgs(args=getter_args)
        )
        self.templates.assert_structure("getter", getter_response)
        bundle_result = await client.validate_bundle_hash(bundle_hash=bundle_hash)
        self.templates.assert_structure("bundle_validation", bundle_result)
