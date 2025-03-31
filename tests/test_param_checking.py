import os
import json
import unittest
from libsimba import SearchFilter, FieldFilter, FilterOp
from libsimba.param_checking import ParamChecking
from libsimba.utils import Path
import respx
import re
from httpx import Response
import pytest

data = os.path.join(os.path.dirname(__file__), "data", "test-contract.json")
with open(data) as md_file:
    md = json.load(md_file)

metadata_pattern = re.compile(r".*/v2/apps/[\w-]+/contract/[\w-]+/\?format=json$")

login_pattern = re.compile(r".*/o/token.*")

md_mock = respx.mock(assert_all_mocked=True, assert_all_called=False)

login_route = md_mock.route(method="POST", url=login_pattern).mock(
    return_value=Response(
        200,
        json={"access_token": "1234567890", "token_type": "Bearer", "expires_in": 200},
    )
)

metadata_route = md_mock.route(method="GET", url=metadata_pattern).mock(
    return_value=Response(
        200,
        json=md,
    )
)


class ParamTestCase(unittest.TestCase):

    @pytest.mark.unit
    @md_mock
    def test_getter(self):
        pcc = ParamChecking("my_app", "my_api")
        pcc.validate_params(
            method_name="getTestData",
            inputs={
                "tokenId": 1234
            },
        )
        err = None
        try:
            pcc.validate_params(
                method_name="getTestData",
                inputs={
                    "foo": True
                },
            )
        except ValueError as ve:
            err = ve
            print(err)
            assert "Unexpected keys." in f"{ve}"
        assert err is not None
        err = None
        try:
            pcc.validate_params(
                method_name="getTestData",
                inputs={
                    "tokenId": "foo"
                },
            )
        except ValueError as ve:
            err = ve
            print(err)
            assert "invalid literal for int() with base 10" in f"{ve}"
        assert err is not None

    @pytest.mark.unit
    @md_mock
    def test_struct(self):
        pcc = ParamChecking("my_app", "my_api")
        pcc.validate_params(
            method_name="structTest_5",
            inputs={
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
        )
        err = None
        try:
            pcc.validate_params(
                method_name="structTest_5",
                inputs={
                    "person": {
                        "name": "The Laughing Gnome",
                        "age": 32,
                        "addr": {
                            "street": "Happy Street",
                            "number": -10,
                            "town": "Funsville",
                        },
                    }
                },
            )
        except ValueError as ve:
            err = ve
            assert "Expected non negative int but got -10" in f"{ve}"
        assert err is not None

    @pytest.mark.unit
    @md_mock
    def test_arrs(self):
        pcc = ParamChecking("my_app", "my_api")
        pcc.validate_params(
            method_name="nested_arr_1",
            inputs={"first": [[1, 2], [1, 2, 3, 4], [2], [], [1, 2, 3, 4, 5, 6, 7]]},
        )
        pcc.validate_params(
            method_name="nested_arr_2", inputs={"first": [[1, 2, 3, 4], [1, 2, 3, 4]]}
        )
        pcc.validate_params(
            method_name="nested_arr_3",
            inputs={"first": [[1, 2, 3], [1, 2, 3], [1, 2, 3]]},
        )
        err = None
        try:
            pcc.validate_params(
                method_name="nested_arr_2",
                inputs={"first": [[1, 2, 3, 4, 5], [1, 2, 3, 4]]},
            )
        except ValueError as ve:
            err = ve
            assert "Expected 4 but got 5" in f"{ve}"
        assert err is not None
        err = None
        try:
            pcc.validate_params(
                method_name="nested_arr_3", inputs={"first": [[1, 2, 3], [1, 2, 3]]}
            )
        except ValueError as ve:
            err = ve
            assert "Expected 3 but got 2" in f"{ve}"
        assert err is not None

    @pytest.mark.unit
    @md_mock
    def test_struct_arrs(self):
        pcc = ParamChecking("my_app", "my_api")

        pcc.validate_params(
            method_name="structTest_4",
            inputs={
                "persons": [
                    {
                        "name": "The Laughing Gnome",
                        "age": 32,
                        "addrs": [
                            {
                                "street": "Happy Street",
                                "number": 10,
                                "town": "Funsville",
                            }
                        ],
                    },
                    {
                        "name": "The Laughing Gnome",
                        "age": 32,
                        "addrs": [
                            {
                                "street": "Happy Street",
                                "number": 10,
                                "town": "Funsville",
                            },
                            {
                                "street": "Happy Street",
                                "number": 10,
                                "town": "Funsville",
                            },
                        ],
                    },
                ]
            },
        )
        err = None
        try:
            pcc.validate_params(
                method_name="structTest_4",
                inputs={
                    "persons": [
                        {
                            "name": "The Laughing Gnome",
                            "age": 32,
                            "addrs": [
                                {
                                    "street": "Happy Street",
                                    "number": 10,
                                    "town": "Funsville",
                                }
                            ],
                        },
                        {
                            "name": "The Laughing Gnome",
                            "age": 32,
                            "addrs": {
                                "street": "Happy Street",
                                "number": 10,
                                "town": "Funsville",
                            }
                        },
                    ]
                },
            )
        except ValueError as ve:
            err = ve
            print(ve)
            assert "Expected a list for key: addrs" in f"{ve}"
        assert err is not None

    def test_paths(self):
        p = Path.CONTRACT_TXN
        ex = None
        try:
            _ = p.create("org", "0x1234")
        except Exception as e:
            ex = e
        self.assertIsNotNone(ex)
        ex = None
        try:
            _ = p.create("app", "org", "0x1234", "extra")
        except Exception as e:
            ex = e
        self.assertIsNotNone(ex)
        formatted = p.create("app", "org", "0x1234")
        self.assertEqual("/v2/apps/app/contract/org/transactions/0x1234/", formatted)

    def test_query_serialization(self):
        params = SearchFilter()
        params.add_filter(
            FieldFilter(field="owner_type", op=FilterOp.EQ, value="User")
        )

        params.add_filter(
            FieldFilter(field="owner_identifier", op=FilterOp.EQ, value="franz@kakfa.org")
        )

        params.add_filter(
            FieldFilter(field="alias", op=FilterOp.EQ, value="my alias")
        )
        params.add_filter(
            FieldFilter(field="networks", op=FilterOp.EQ, value="quorum-foo-bar")
        )
        params.add_filter(
            FieldFilter(field="num", op=FilterOp.GTE, value=3)
        )
        params.add_filter(
            FieldFilter(field="lst", op=FilterOp.IN, value=[1, 2, 3])
        )
        self.assertEqual({
            "owner_type": "User",
            "owner_identifier": "franz@kakfa.org",
            "alias": "my alias",
            "networks": "quorum-foo-bar",
            "num__gte": 3, "lst__in": "1,2,3"
        }, params.query)
        self.assertEqual({
            "filter[owner_type]": "User",
            "filter[owner_identifier]": "franz@kakfa.org",
            "filter[alias]": "my alias",
            "filter[networks]": "quorum-foo-bar",
            "filter[num.gte]": 3,
            "filter[lst.in]": "1,2,3"
        }, params.filter_query)
