from dotenv import load_dotenv
from datetime import datetime
from faker import Faker
import uuid
import os

from app.dbo.transcription_dbo import TranscriptionDBO
from tests.conftest import db_session, test_client

load_dotenv()
fake = Faker()


def test_rewiew_response(db_session, test_client):
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
                "dados_do_paciente.peso": "80kg",
            },
        },
    )

    db_session.add(new_transcription)
    db_session.commit()
    db_session.refresh(new_transcription)

    rewiew_response_response = test_client.post(
        f"{base_url}/medai/rewiew_response",
        json={
            "transcription_id": new_transcription.id,
            "reviewed_response": {
                "dados_do_paciente.sexo": "Feminino",
                "dados_do_paciente.altura": "1.80m",
            },
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )
    response_json = rewiew_response_response.json()

    assert response_json == ["Resposta salva com sucesso"]

    db_session.refresh(new_transcription)

    structured_json = new_transcription.response_json["structured_json"]
    assert structured_json["dados_do_paciente.sexo"] == "Feminino"
    assert structured_json["dados_do_paciente.altura"] == "1.80m"
