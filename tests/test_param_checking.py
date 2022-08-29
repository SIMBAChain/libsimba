import json
import unittest
from libsimba.param_checking import ParamChecking
import respx
import re
from httpx import Response

with open("./data/test-contract.json") as md_file:
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
