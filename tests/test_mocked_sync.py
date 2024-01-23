import unittest
from copy import deepcopy
import respx
import re
from typing import List, Tuple, Any
from tests import run_sync
from tests.validate import Templates
from httpx import Response
from libsimba import SimbaSync
import pytest

tpl = Templates()
runner = run_sync.SyncRunner()


def make_type(model: str, replace: List[Tuple[str, Any]] = None) -> dict:
    structure = tpl.types.get(model)
    print()
    print(f"MODEL: {model}, DATA: {structure}")
    replace = replace or []
    for rep in replace:
        if structure.get(rep[0]):
            structure[rep[0]] = rep[1]
    return structure


def make_list(model: str, length: int = 3) -> list:
    structure = tpl.types.get(model)
    print(f"MODEL: {model}, DATA: {structure}")
    ret = []
    for i in range(length):
        ret.append(deepcopy(structure))
    return ret


def make_results(model: str, length: int = 3) -> dict:
    structure = tpl.types.get(model)
    print(f"MODEL: {model}, DATA: {structure}")
    ret = []
    for i in range(length):
        ret.append(deepcopy(structure))
    return {"count": length, "next": None, "results": ret}


login_pattern = re.compile(r".*/o/token.*")
org_pattern = re.compile(r".*/v2/organisations/[\w-]+/$")
blockchains_pattern = re.compile(r".*/v2/organisations/[\w-]+/blockchains/$")
storage_pattern = re.compile(r".*/v2/organisations/[\w-]+/storage/$")
apps_pattern = re.compile(r".*/v2/organisations/[\w-]+/applications/$")
app_pattern = re.compile(r".*/v2/organisations/[\w-]+/applications/[\w-]+/$")
designs_pattern = re.compile(r".*/v2/organisations/[\w-]+/contract_designs/$")
artifacts_pattern = re.compile(r".*/v2/organisations/[\w-]+/contract_artifacts/$")
deployment_pattern = re.compile(r".*/v2/organisations/[\w-]+/deployments/[\w-]+/$")
deployments_pattern = re.compile(r".*/v2/organisations/[\w-]+/deployments/$")
libraries_pattern = re.compile(r".*/v2/organisations/[\w-]+/deployments/library/$")
transaction_pattern = re.compile(r"/v2/organisations/[\w-]+/transactions/[\w-]+/$")
method_pattern = re.compile(r"/v2/apps/[\w-]+/contract/[\w-]+/[\w-]+/$")
query_method_pattern = re.compile(r"/v2/apps/[\w-]+/contract/[\w-]+/[\w-]+/\?.*$")

abi_pattern = re.compile(r"/services/blockchains/.+/contracts/.+/abi/$")
accounts_pattern = re.compile(r"/user/accounts/$")
account_pattern = re.compile(r"/user/accounts/[\w-]+/$")
accounts_sign_pattern = re.compile(r"/user/accounts/.+/sign/$")


block_mock = respx.mock(assert_all_mocked=True, assert_all_called=False)

login_route = block_mock.route(method="POST", url=login_pattern).mock(
    return_value=Response(
        200,
        json={"access_token": "1234567890", "token_type": "Bearer", "expires_in": 200},
    )
)

whoami_route = block_mock.route(method="GET", path="/user/whoami/").mock(
    return_value=Response(200, json=make_type("user"))
)

blockchains_route = block_mock.route(method="GET", url=blockchains_pattern).mock(
    return_value=Response(200, json=make_results("blockchain"))
)

storage_route = block_mock.route(method="GET", url=storage_pattern).mock(
    return_value=Response(200, json=make_results("storage"))
)

get_org_route = block_mock.route(method="GET", url=org_pattern).mock(
    return_value=Response(200, json=make_type("organisation"))
)

get_apps_route = block_mock.route(method="GET", url=apps_pattern).mock(
    return_value=Response(200, json=make_results("application"))
)

post_apps_route = block_mock.route(method="POST", url=apps_pattern).mock(
    return_value=Response(
        200, json=make_type("application", replace=[("name", runner.name)])
    )
)

get_app_route = block_mock.route(method="GET", url=app_pattern).mock(
    return_value=Response(404, json={})
)

post_designs_route = block_mock.route(method="POST", url=designs_pattern).mock(
    return_value=Response(
        200,
        json=make_type(
            "contract_design", replace=[("id", "1234"), ("name", "libsimba")]
        ),
    )
)

get_designs_route = block_mock.route(method="GET", url=designs_pattern).mock(
    return_value=Response(200, json=make_results("contract_design"))
)

post_artifacts_route = block_mock.route(method="POST", url=artifacts_pattern).mock(
    return_value=Response(
        200,
        json=make_type(
            "contract_artifact", replace=[("id", "1234"), ("name", "libsimba")]
        ),
    )
)

get_artifacts_route = block_mock.route(method="GET", url=artifacts_pattern).mock(
    return_value=Response(200, json=make_results("contract_artifact"))
)

post_deployment_route = block_mock.route(method="POST", url=deployments_pattern).mock(
    return_value=Response(
        200, json=make_type("deployment", replace=[("state", "COMPLETED")])
    )
)

get_deployment_route = block_mock.route(method="GET", url=deployment_pattern).mock(
    return_value=Response(
        200, json=make_type("deployment", replace=[("state", "COMPLETED")])
    )
)

get_transaction_route = block_mock.route(method="GET", url=transaction_pattern).mock(
    return_value=Response(
        200, json=make_type("transaction", replace=[("state", "COMPLETED")])
    )
)

post_method_route = block_mock.route(method="POST", url=method_pattern).mock(
    return_value=Response(
        200, json=make_type("transaction", replace=[("state", "ACCEPTED")])
    )
)

get_method_route = block_mock.route(method="GET", url=query_method_pattern).mock(
    return_value=Response(200, json=make_results("transaction", length=2))
)

get_abi_route = block_mock.route(method="GET", url=abi_pattern).mock(
    return_value=Response(200, json=make_type("abi"))
)

get_accounts_route = block_mock.route(method="GET", url=accounts_pattern).mock(
    return_value=Response(200, json=make_results("account"))
)

get_account_route = block_mock.route(method="GET", url=account_pattern).mock(
    return_value=Response(200, json=make_type("account"))
)

accounts_sign_route = block_mock.route(method="POST", url=accounts_sign_pattern).mock(
    return_value=Response(200, json=make_type("signature"))
)

libraries_route = block_mock.route(method="POST", url=libraries_pattern).mock(
    return_value=Response(200, json=make_type("deployment_response"))
)


class SyncApp(unittest.TestCase):
    @pytest.mark.unit
    @block_mock
    def test_mocked(self):
        simba = SimbaSync()
        runner.me(simba=simba)
        runner.blockchains(simba=simba)
        runner.storage(simba=simba)
        runner.accounts(simba=simba)
        runner.org_app(simba=simba)
        name, design_id = runner.designs(simba=simba)
        app, api_name, address, contract_id = runner.artifacts(
            simba=simba,
            design_id=design_id,
            app=runner.name,
            api_name=runner.name,
            blockchain=runner.blockchain_name,
            storage=runner.storage_name,
        )
        print(
            f"app: {app}, api_name: {api_name}, address: {address}, contract_id: {contract_id}"
        )
        runner.contract(simba=simba, org=runner.org, app=app, api_name=api_name)
        runner.query(simba=simba, app=app, api_name=api_name)
