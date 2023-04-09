import os
from libsimba import (
    SimbaSync,
    SearchFilter,
    FieldFilter,
    FilterOp,
    MethodCallArgs,
    File,
    FileDict,
)
import time
from tests.validate import Templates
from typing import Tuple, List, Union, Optional
import shutil
import tarfile
import traceback


class Runner(object):
    def __init__(
        self,
        org: str = "libsimba",
        blockchain_name: str = "Quorum",
        storage_name: str = "azure",
        num_calls: int = 10,
        now: Optional[int] = int(time.time())
    ):
        self.org = org
        self.blockchain_name = blockchain_name
        self.storage_name = storage_name
        self.num_calls = num_calls
        self.name = f"libsimba-{now}"
        self.display = f"LibSimba-{now}"
        self.templates = Templates()
        self.errors = []

    def capture_error(self):
        self.errors.append(traceback.format_exc())

    def get_errors(self):
        return "==============\n\n".join(self.errors)

    def has_errors(self):
        return len(self.errors) > 0

    def file_paths(self) -> Tuple[str, str, str]:
        data_dir = os.path.join(os.path.dirname(__file__), "output")
        os.makedirs(data_dir, exist_ok=True)
        zip_path = os.path.join(data_dir, "out.tar.gz")
        file_path = os.path.join(data_dir, "out.txt")
        return data_dir, zip_path, file_path

    def test_file_name(self) -> str:
        return "f1.txt"

    def check_files(self, data_dir: str, zip_path: str, file_path: str):
        orig_dir = os.path.join(os.path.dirname(__file__), "data")
        tf = tarfile.open(zip_path)
        unzipped = os.path.join(data_dir, "out")
        os.makedirs(unzipped, exist_ok=True)
        tf.extractall(unzipped)
        with open(os.path.join(unzipped, "f1.txt"), "r") as f1, open(
            os.path.join(orig_dir, "file1.txt"), "r"
        ) as f1_orig:
            assert f1.read() == f1_orig.read()
        with open(os.path.join(unzipped, "f2.txt"), "r") as f2, open(
            os.path.join(orig_dir, "file2.txt"), "r"
        ) as f2_orig:
            assert f2.read() == f2_orig.read()
        with open(os.path.join(file_path), "r") as f1, open(
            os.path.join(orig_dir, "file1.txt"), "r"
        ) as f1_orig:
            assert f1.read() == f1_orig.read()
        shutil.rmtree(data_dir)

    def bundle_function(self) -> str:
        return "structTest_5"

    def query_function(self) -> str:
        return "structTest_2"

    def event_function(self) -> str:
        return "mint"

    def call_function(self) -> str:
        return "getTestData"

    def event_name(self) -> str:
        return "Transfer"

    def bundle_inputs(self) -> Tuple[dict, FileDict]:
        orig_dir = os.path.join(os.path.dirname(__file__), "data")
        return (
            {
                "person": {
                    "name": "The Laughing Gnome",
                    "age": 32,
                    "addr": {
                        "street": "Happy Street",
                        "number": 10,
                        "town": "Funsville",
                    },
                }
            },
            FileDict(
                files=[
                    File(path=os.path.join(orig_dir, "file1.txt"), name="f1.txt", mime="text/plain"),
                    File(path=os.path.join(orig_dir, "file2.txt"), name="f2.txt", mime="text/plain"),
                ]
            ),
        )

    def query_inputs(self) -> List[dict]:
        ret = []
        for i in range(self.num_calls):
            inputs = {
                "person": {
                    "name": f"The Laughing Gnome {i + 1}",
                    "age": i + 1,
                    "addr": {
                        "street": "Happy Street",
                        "number": i + 1,
                        "town": "Funsville",
                    },
                },
                "test_bool": True,
            }
            ret.append(inputs)
        return ret

    def call_inputs(self) -> List[dict]:
        ret = []
        for i in range(self.num_calls):
            inputs = {"data": "Foo", "moreData": f"Fighters {i}"}
            ret.append(inputs)
        return ret

    def call_inputs_again(self) -> List[dict]:
        ret = []
        for i in range(self.num_calls):
            inputs = {"data": "Fool", "moreData": f"Fighters {i}"}
            ret.append(inputs)
        return ret

    def getter_args(self, event_dict: dict) -> dict:
        return {"tokenId": event_dict.get("tokenId")}

    def get_fields(
        self, data: Union[dict, List[dict]], field: str = "name"
    ) -> List[str]:
        if isinstance(data, dict):
            data = data.get("results", [])
        return [obj.get(field) for obj in data]


class SyncRunner(Runner):
    def run(self):
        simba = SimbaSync()
        print("================ checking me ================")
        try:
            self.me(simba)
        except Exception:
            self.capture_error()
        print("================ checking blockchains ================")
        try:
            chains = self.blockchains(simba)
            assert self.blockchain_name in chains
        except Exception:
            self.capture_error()
        print("================ checking storage ================")
        try:
            offchains = self.storage(simba)
            assert self.storage_name in offchains
        except Exception:
            self.capture_error()
        try:
            self.org_app(simba)
            print("================ checking designs ================")
            design_name, design_id = self.designs(simba)
            print(f"Saved design: {design_name} with id: {design_id}")
        except Exception:
            self.capture_error()
            raise ValueError(self.get_errors())

        print("================ checking deploy ================")
        try:
            app, api_name, address, contract_id = self.artifacts(
                simba=simba,
                design_id=design_id,
                app=self.name,
                api_name=self.name,
                blockchain=self.blockchain_name,
                storage=self.storage_name,
            )
            print(f"Deployed contract: {address} with id: {contract_id}")

            print("================ checking transactions ================")
            txn_data = self.contract(
                simba=simba, app=app, org=self.org, api_name=api_name
            )
            bundle_hash = txn_data.get("inputs", {}).get("_bundleHash")
            print("================ checking bundles ================")
            manifest = self.files(
                simba=simba, app=app, api_name=api_name, bundle_hash=bundle_hash
            )
            print(manifest)
            print("================ checking query ================")
            self.query(simba=simba, app=app, api_name=api_name)
            print("================ checking getter ================")
            event_list = self.event_and_getter(
                simba=simba, app=app, api_name=api_name
            )
            print("================ checking contract client ================")
            self.contract_client(
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


    def me(self, simba: SimbaSync):
        me = simba.whoami()
        print(me)
        self.templates.assert_structure("user", me)

    def blockchains(self, simba: SimbaSync) -> List[str]:
        blockchains = simba.get_blockchains(org=self.org)
        print(blockchains)
        self.templates.assert_structure("blockchain", blockchains, many=True)
        return self.get_fields(blockchains)

    def storage(self, simba: SimbaSync) -> List[str]:
        storage = simba.get_storage(org=self.org)
        print(storage)
        self.templates.assert_structure("storage", storage, many=True)
        return self.get_fields(storage)

    def org_app(self, simba: SimbaSync):
        org_data = simba.create_org(name=self.org, display=self.org)
        print(org_data)
        self.templates.assert_structure("organisation", org_data)
        app_data = simba.create_app(org=self.org, name=self.name, display=self.display)
        print(app_data)
        self.templates.assert_structure("application", app_data)
        self.templates.assert_value(type_name="application", data=app_data, value=self.name, path="name")

    def designs(self, simba: SimbaSync) -> Tuple[str, str]:
        designs = simba.get_designs(org=self.org)
        self.templates.assert_structure("contract_design", designs, many=True, action="list")

        contract = os.path.join(os.path.dirname(__file__), "data", "TestContract.sol")

        with open(contract, "r") as sol:
            code = sol.read()
        saved_data = simba.save_design(
            org=self.org,
            name=self.name,
            code=code,
            target_contract="TestContract",
            binary_targets=["TestContract"],
        )
        self.templates.assert_structure("contract_design", saved_data)
        return saved_data.get("name"), saved_data.get("id")

    def artifacts(
        self,
        simba: SimbaSync,
        design_id: str,
        app: str,
        api_name: str,
        storage: str,
        blockchain: str,
    ) -> Tuple[str, str, str, str]:
        artifacts = simba.get_artifacts(org=self.org)
        self.templates.assert_structure("contract_artifact", artifacts, many=True)
        artifact_data = simba.create_artifact(org=self.org, design_id=design_id)
        address, contract_id = simba.wait_for_deploy_artifact(
            org=self.org,
            app=app,
            api_name=api_name,
            artifact_id=artifact_data["id"],
            storage=storage,
            blockchain=blockchain,
        )
        return app, api_name, address, contract_id

    def contract(self, simba: SimbaSync, org: str, app: str, api_name: str) -> dict:

        inputs, files = self.bundle_inputs()

        txn = simba.submit_contract_method(
            app_id=app,
            contract_name=api_name,
            method_name=self.bundle_function(),
            inputs=inputs,
            files=files,
        )
        completed_with_bundle = simba.wait_for_org_transaction(
            org=org, uid=txn.get("id")
        )
        print(completed_with_bundle)
        self.templates.assert_structure("transaction", completed_with_bundle)

        txn = None
        input_list = self.query_inputs()
        for input in input_list:
            txn = simba.submit_contract_method(
                app_id=app,
                contract_name=api_name,
                method_name=self.query_function(),
                inputs=input,
            )
        done = simba.wait_for_org_transaction(org=org, uid=txn.get("id"))
        print(done)
        return completed_with_bundle

    def query(self, simba: SimbaSync, app: str, api_name: str):
        query = SearchFilter(
            filters=[
                FieldFilter(field="inputs.person.age", op=FilterOp.GT, value=2),
            ],
            fields=["state", "transaction_hash", "inputs"],
            limit=2,
            offset=0,
        )
        gen = simba.list_transactions_by_method(
            app_id=app,
            contract_name=api_name,
            method_name=self.query_function(),
            query_args=query,
        )
        for result in gen:
            print(result)
            assert len(result) == 2 or len(result) == 1

    def files(
        self, simba: SimbaSync, app: str, api_name: str, bundle_hash: str
    ) -> dict:
        manifest = simba.get_manifest_for_bundle_from_bundle_hash(
            app_id=app, contract_name=api_name, bundle_hash=bundle_hash
        )
        self.templates.assert_structure("manifest", manifest)
        data_dir, zip_path, file_path = self.file_paths()
        simba.get_bundle(
            app_id=app,
            contract_name=api_name,
            bundle_hash=bundle_hash,
            download_location=zip_path,
        )
        simba.get_bundle_file(
            app_id=app,
            contract_name=api_name,
            bundle_hash=bundle_hash,
            file_name=self.test_file_name(),
            download_location=file_path,
        )
        self.check_files(data_dir=data_dir, zip_path=zip_path, file_path=file_path)
        return manifest

    def event_and_getter(self, simba: SimbaSync, app: str, api_name: str) -> List[dict]:
        call_inputs = self.call_inputs_again()
        txn = None
        for input in call_inputs:
            txn = simba.submit_contract_method(
                app_id=app,
                contract_name=api_name,
                method_name=self.event_function(),
                inputs=input,
            )
        done = simba.wait_for_org_transaction(org=self.org, uid=txn.get("id"))
        print(done)
        events = simba.get_events(
            app_id=app, contract_name=api_name, event_name=self.event_name()
        )
        event_inputs = []
        for event in events:
            self.templates.assert_structure("event", event)
            event_input = event.get("inputs")
            event_inputs.append(self.getter_args(event_input))
            args = self.getter_args(event_input)
            getter_result = simba.call_contract_method(
                app_id=app,
                contract_name=api_name,
                method_name=self.call_function(),
                args=MethodCallArgs(args=args),
            )
            self.templates.assert_structure("getter", getter_result)
        return event_inputs

    def contract_client(
        self,
        simba: SimbaSync,
        app: str,
        api_name: str,
        bundle_hash: str,
        getter_args: dict,
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
        txns = client.get_method_transactions(
            query_args=query, method_name=self.query_function()
        )
        self.templates.assert_structure("transaction_fields", txns, many=True)
        getter_response = client.call_method(
            method_name=self.call_function(), args=MethodCallArgs(args=getter_args)
        )
        self.templates.assert_structure("getter", getter_response)
        bundle_result = client.validate_bundle_hash(bundle_hash=bundle_hash)
        self.templates.assert_structure("bundle_validation", bundle_result)
