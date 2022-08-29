from unittest import IsolatedAsyncioTestCase
from tests.test_mocked_sync import block_mock
from tests.run_async import AsyncRunner
from libsimba import Simba


class AsyncApp(IsolatedAsyncioTestCase):
    @block_mock
    async def test_mocked(self):
        simba = Simba()
        arunner = AsyncRunner()
        await arunner.me(simba=simba)
        await arunner.blockchains(simba=simba)
        await arunner.storage(simba=simba)
        await arunner.org_app(simba=simba)
        name, design_id = await arunner.designs(simba=simba)
        app, api_name, address, contract_id = await arunner.artifacts(
            simba=simba,
            design_id=design_id,
            app=arunner.name,
            api_name=arunner.name,
            blockchain=arunner.blockchain_name,
            storage=arunner.storage_name,
        )
        print(
            f"app: {app}, api_name: {api_name}, address: {address}, contract_id: {contract_id}"
        )
        await arunner.contract(simba=simba, org=arunner.org, app=app, api_name=api_name)
        await arunner.query(simba=simba, app=app, api_name=api_name)
