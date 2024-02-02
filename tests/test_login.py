import unittest
import respx
import re
from httpx import Response
from libsimba import Login, AuthFlow, SimbaRequest, ConnectionConfig
from libsimba.auth import AuthProvider, AuthToken
from libsimba.config import settings
import pytest

login_pattern = re.compile(r".*/o/token.*")

block_mock = respx.mock(assert_all_mocked=True, assert_all_called=False)

login_route = block_mock.route(method="POST", url=login_pattern).mock(
    return_value=Response(
        200,
        json={"access_token": "1234567890", "token_type": "Bearer", "expires_in": 200},
    )
)

whoami_route = block_mock.route(method="GET", path="/user/whoami/").mock(
    return_value=Response(200, json={"name": "baz"})
)


class MockClass:
    def test_func(self, headers: dict = None, payload=None, login: Login = None):
        headers = SimbaRequest.login(login=login, headers=headers or {})
        return headers, payload


class TestAuthRequired(unittest.TestCase):
    @pytest.mark.unit
    @block_mock
    def test_auth_required_no_params(self):
        mc = MockClass()
        resp = mc.test_func(
            login=Login(
                auth_flow=AuthFlow.CLIENT_CREDENTIALS,
                client_id="me",
                client_secret="topsecret",
            )
        )
        self.assertEqual(({"Authorization": "Bearer 1234567890"}, None), resp)

    @pytest.mark.unit
    @block_mock
    def test_auth_required_headers(self):
        mc = MockClass()
        resp = mc.test_func(
            headers={"bob": "test"},
            payload={},
            login=Login(
                auth_flow=AuthFlow.CLIENT_CREDENTIALS,
                client_id="me",
                client_secret="topsecret",
            ),
        )
        self.assertEqual(
            ({"bob": "test", "Authorization": "Bearer 1234567890"}, {}), resp
        )

    @pytest.mark.unit
    @block_mock
    def test_auth_from_headers(self):
        mc = MockClass()
        resp = mc.test_func(
            headers={"Authorization": "Bearer 10000000000000"},
            payload={},
            login=Login(
                auth_flow=AuthFlow.CLIENT_CREDENTIALS,
                client_id="me",
                client_secret="topsecret",
            ),
        )
        self.assertEqual(
            ({"Authorization": "Bearer 10000000000000"}, {}), resp
        )

    @pytest.mark.unit
    @block_mock
    def test_auth_from_headers(self):
        mc = MockClass()
        resp = mc.test_func(
            headers={"Authorization": "Bearer 10000000000000", "bob": "test"},
            payload={},
            login=Login(
                auth_flow=AuthFlow.CLIENT_CREDENTIALS,
                client_id="me",
                client_secret="topsecret",
            ),
        )
        self.assertEqual(
            ({"bob": "test", "Authorization": "Bearer 10000000000000"}, {}), resp
        )

    def test_token_expired(self) -> None:


        token = AuthToken(**{
            "token": "64YU6BPTqM6SJcrYbbkgVtOjRy3zgx",
            "type": "Bearer",
            "expires": "2024-01-24T08:21:11.190578"}
        )

        class TestProvider(AuthProvider):
            async def login(self, client_id: str, client_secret: str, config: ConnectionConfig = None) -> AuthToken:
                return token

            def login_sync(self, client_id: str, client_secret: str, config: ConnectionConfig = None) -> AuthToken:
                return token

        prov = TestProvider()
        client_id = "me"

        print(prov.get_cached_token(client_id=client_id))
