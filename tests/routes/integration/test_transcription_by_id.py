import uuid
from dotenv import load_dotenv
from datetime import datetime
from faker import Faker
import os

from app.dbo.transcription_dbo import TranscriptionDBO
from tests.conftest import db_session, test_client

load_dotenv()
fake = Faker()


def test_transcription_by_id(db_session, test_client):
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

    doctor_id = uuid.uuid4()
    new_transcription = TranscriptionDBO(
        user_id=1,
        patient_name=fake.name(),
        patient_cpf="1234567890",
        patient_phone=fake.phone_number(),
        doctor_id=doctor_id,
        audio_url=fake.url(),
        document_template_id=uuid.uuid4(),
        raw_transcription="Test Transcription",
        transcription_date=datetime.now(),
        response_json={
            "status_code": 200,
            "raw": "Test Transcription",
            "structured_json": {
                "dados_do_paciente.sexo": "Masculino",
            },
        },
    )

    db_session.add(new_transcription)
    db_session.commit()
    db_session.refresh(new_transcription)

    transcription_by_id_response = test_client.get(
        f"{base_url}/medai/transcriber/transcription_by_id/{new_transcription.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    response_json = transcription_by_id_response.json()

    assert response_json["response"]["status_code"] == 200
    assert response_json["id"] == new_transcription.id
    assert response_json["doctor_id"] == str(doctor_id)
    assert response_json["patient_name"] == new_transcription.patient_name
    assert response_json["patient_cpf"] == new_transcription.patient_cpf
    assert response_json["patient_phone"] == new_transcription.patient_phone
    assert response_json["raw_transcription"] == "Test Transcription"
    assert response_json["response"]["raw"] == "Test Transcription"
    assert response_json["response"]["structured_json"] is not None
    assert response_json["user_id"] == 1
