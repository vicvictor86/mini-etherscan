import uuid
from dotenv import load_dotenv
from datetime import datetime
from faker import Faker
import os

from app.dbo.transcription_dbo import TranscriptionDBO

from tests.conftest import db_session, test_client

load_dotenv()
fake = Faker()


def test_get_audio_presigned(db_session, test_client):
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

    audio_url = fake.first_name()
    new_transcription = TranscriptionDBO(
        user_id=1,
        patient_name=fake.name(),
        patient_cpf="1234567890",
        patient_phone=fake.phone_number(),
        doctor_id=uuid.uuid4(),
        audio_url=audio_url,
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

    get_audio_resigned_response = test_client.get(
        f"{base_url}/medai/transcriber/get_audio_presigned",
        params={
            "transcription_id": new_transcription.id,
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )
    response_json = get_audio_resigned_response.json()

    assert response_json["status_code"] == 200
    assert audio_url in response_json["presigned_url"]
