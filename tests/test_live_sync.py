import unittest
from tests import run_sync


class TestApp(unittest.TestCase):
    def test_all(self):
        run_sync.SyncRunner().run()
