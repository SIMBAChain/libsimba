from tests import run_async
from unittest import IsolatedAsyncioTestCase
import pytest


class GenTestCase(IsolatedAsyncioTestCase):
    @pytest.mark.skip(reason="Requires Live server")
    async def test_all(self):
        await run_async.AsyncRunner().run()
