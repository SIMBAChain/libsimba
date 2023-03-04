import unittest
from unittest.mock import patch
import logging
import pytest
from libsimba import SimbaSync, TxnHeaders


logger = logging.getLogger(__name__)


class TestSimba(unittest.TestCase):
    def setUp(self):
        self.simba = SimbaSync()
        patcher_send = patch("libsimba.simba_request.SimbaRequest.send_sync")
        self.addCleanup(patcher_send.stop)
        self.mock_send = patcher_send.start()

    @pytest.mark.unit
    def test_submit_contract_method(self):
        resp = self.simba.submit_contract_method(
            app_id="app_id",
            contract_name="contract",
            method_name="method",
            inputs={"key": "value"},
        )
        self.mock_send.assert_called_once_with(
            headers={}, json_payload={"key": "value"}, files=None, config=None
        )

    @pytest.mark.unit
    def test_submit_contract_method_with_params(self):
        resp = self.simba.submit_contract_method(
            app_id="app_id",
            contract_name="contract",
            method_name="method",
            inputs={"key": "value"},
            txn_headers=TxnHeaders(sender="0x1773"),
        )
        self.mock_send.assert_called_once_with(
            headers={"txn-sender": "0x1773"},
            json_payload={"key": "value"},
            files=None,
            config=None,
        )

    @pytest.mark.unit
    def test_submit_contract_method_async(self):
        resp = self.simba.submit_contract_method_sync(
            app_id="app_id",
            contract_name="contract",
            method_name="method",
            inputs={"key": "value"},
        )
        self.mock_send.assert_called_once_with(
            headers={}, json_payload={"key": "value"}, files=None, config=None
        )

    @pytest.mark.unit
    def test_submit_contract_method_async_with_params(self):
        resp = self.simba.submit_contract_method_sync(
            app_id="app_id",
            contract_name="contract",
            method_name="method",
            inputs={"key": "value"},
            txn_headers=TxnHeaders(sender="0x1773"),
        )
        self.mock_send.assert_called_once_with(
            headers={"txn-sender": "0x1773"},
            json_payload={"key": "value"},
            files=None,
            config=None,
        )

    @pytest.mark.unit
    def test_submit_signed_transaction(self):
        resp = self.simba.submit_signed_transaction(
            app_id="app_id",
            txn_id="tnx-id",
            txn={"txn": "data"},
        )
        self.mock_send.assert_called_once_with(
            headers=None,
            json_payload={"transaction": {"txn": "data"}},
            files=None,
            config=None,
        )

    @pytest.mark.unit
    def test_submit_signed_transaction_with_params(self):
        logger.debug("HELLOOOOO")
        resp = self.simba.submit_signed_transaction(
            app_id="app_id",
            txn_id="tnx-id",
            txn={"txn": "data"},
        )
        self.mock_send.assert_called_once_with(
            headers=None,
            json_payload={"transaction": {"txn": "data"}},
            files=None,
            config=None,
        )
