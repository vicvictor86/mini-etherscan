from dotenv import load_dotenv
import os

from tests.conftest import test_client

load_dotenv()


def test_auth(test_client):
    base_url = os.getenv("BASE_URL")

    auth_response = test_client.post(
        f"{base_url}/medai/auth/token",
        data={
            "username": os.getenv("ADMIN_USERNAME"),
            "password": os.getenv("ADMIN_PASSWORD"),
        },
    )
    auth_response_json = auth_response.json()

    assert auth_response_json["access_token"] is not None
    assert auth_response_json["token_type"] == "bearer"
