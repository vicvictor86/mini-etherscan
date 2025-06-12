from dotenv import load_dotenv
from faker import Faker
import json
import uuid
import os

from app.dbo.chat_dbo import ChatDBO
from tests.conftest import db_session, test_client
from tests.templates.transcriptions import (
    request_anamnese_dict,
)

load_dotenv()
fake = Faker()


def test_doctor_message(db_session, test_client):
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

    request_anamnese_dict["transcription_text"] = (
        "O paciente está sentindo dor de cabeça a 8 dias."
    )

    doctor_id = str(uuid.uuid4())
    patient_cpf = "12345678111"

    request_anamnese_dict["doctor_id"] = doctor_id
    request_anamnese_dict["patient_cpf"] = patient_cpf

    anamnese_json = json.dumps(request_anamnese_dict, ensure_ascii=False)
    create_transcription_response = test_client.post(
        f"{base_url}/medai/transcriber/transcribe_appointment",
        data={"transcriber_request": anamnese_json},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    create_transcription_response_json = create_transcription_response.json()
    assert create_transcription_response_json["status_code"] == 200

    doctor_message_response = test_client.post(
        f"{base_url}/medai/chat/doctor_message",
        json={
            "doctor_id": doctor_id,
            "patient_cpf": patient_cpf,
            "question": "Qual o sintoma do paciente?",
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )
    doctor_message_response_json = doctor_message_response.json()

    chat_session_id = doctor_message_response_json["chat_session_id"]
    chat_object = (
        db_session.query(ChatDBO)
        .filter(ChatDBO.chat_session_id == chat_session_id)
        .first()
    )

    assert doctor_message_response_json["status_code"] == 200

    assert chat_object is not None
    assert chat_object.doctor_id == doctor_id
    assert chat_object.patient_cpf == patient_cpf

    assert "8" in doctor_message_response_json["message"]
    assert "cabeça" in doctor_message_response_json["message"].lower()
    assert doctor_message_response_json["chat_session_id"] is not None

    doctor_message_response = test_client.post(
        f"{base_url}/medai/chat/doctor_message",
        json={
            "transcription_id": create_transcription_response_json["transcription_id"],
            "question": "Qual o sintoma do paciente?",
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )
    doctor_message_response_json = doctor_message_response.json()

    assert doctor_message_response_json["status_code"] == 200
    assert "8" in doctor_message_response_json["message"]
    assert "cabeça" in doctor_message_response_json["message"].lower()
    assert doctor_message_response_json["chat_session_id"] is not None

    doctor_message_response = test_client.post(
        f"{base_url}/medai/chat/doctor_message",
        json={
            "question": "Bom dia!",
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )
    doctor_message_response_json = doctor_message_response.json()

    assert doctor_message_response_json["status_code"] == 200
