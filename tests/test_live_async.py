from tests import run_async
from unittest import IsolatedAsyncioTestCase


class GenTestCase(IsolatedAsyncioTestCase):
    async def test_all(self):
        await run_async.AsyncRunner().run()
