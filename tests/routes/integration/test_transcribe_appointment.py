from dotenv import load_dotenv
from faker import Faker
import json
import uuid
import os

from tests.conftest import test_client
from tests.templates.transcriptions import (
    example_transcriptions,
    request_anamnese_dict,
)

load_dotenv()
fake = Faker()


def test_transcribe_appointment(test_client):
    base_url = os.getenv("BASE_URL")

    auth_response = test_client.post(
        f"{base_url}/medai/auth/token",
        data={
            "username": os.getenv("ADMIN_USERNAME"),
            "password": os.getenv("ADMIN_PASSWORD"),
        },
    )
    auth_response_json = auth_response.json()
    access_token = auth_response_json["access_token"]

    for transcription in example_transcriptions:
        request_anamnese_dict["transcription_text"] = transcription[
            "transcription_text"
        ]
        request_anamnese_dict["doctor_id"] = str(uuid.uuid4())

        anamnese_json = json.dumps(request_anamnese_dict, ensure_ascii=False)
        response = test_client.post(
            f"{base_url}/medai/transcriber/transcribe_appointment",
            data={"transcriber_request": anamnese_json},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response_json = response.json()

        assert response_json["status_code"] == 200
        assert response_json["transcription_id"] is not None
        assert response_json["raw"] == transcription["transcription_text"]
        assert response_json["structured_json"] is not None
        break
