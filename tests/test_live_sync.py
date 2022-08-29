import unittest
from tests import run_sync
import pytest


class TestApp(unittest.TestCase):
    @pytest.mark.skip(reason="Requires Live server")
    def test_all(self):
        run_sync.SyncRunner().run()
