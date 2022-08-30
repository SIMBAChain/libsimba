from tests import run_async
from unittest import IsolatedAsyncioTestCase
import pytest


class GenTestCase(IsolatedAsyncioTestCase):
    @pytest.mark.skipif("os.environ.get('SDK_QA') is None", eason="Requires Live server")
    async def test_all(self):
        await run_async.AsyncRunner().run()
