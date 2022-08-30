import unittest
from tests import run_sync
import pytest


class TestApp(unittest.TestCase):
    @pytest.mark.skipif("os.environ.get('SDK_QA') is None", reason="Requires Live server")
    def test_all(self):
        run_sync.SyncRunner().run()
