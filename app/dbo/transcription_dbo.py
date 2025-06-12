from datetime import time, datetime, timedelta, timezone
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Sequence,
    String,
    JSON,
    DECIMAL,
)
from app.database import Base
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import UUID
import os


class TranscriptionDBO(Base):
    __tablename__ = "transcriptions"
    id = Column(Integer, Sequence("transcription_id_seq"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    audio_url = Column(String, nullable=True)
    raw_transcription = Column(String, nullable=True)
    transcription_date = Column(
        DateTime, default=datetime.now(timezone.utc), nullable=False
    )
    audio_duration_in_seconds = Column(Integer, nullable=True)

    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)

    structure_model = Column(String, nullable=True)

    transcription_cost = Column(DECIMAL(10, 4), nullable=True)
    structure_cost = Column(DECIMAL(10, 4), nullable=True)

    response = Column(String, nullable=True)
    reviewed_response = Column(String, nullable=True)

    response_json = Column(JSON, nullable=True)
    reviewed_response_json = Column(JSON, nullable=True)

    doctor_id = Column(String, nullable=True)
    patient_cpf = Column(String, nullable=True)
    patient_name = Column(String, nullable=True)
    patient_phone = Column(String, nullable=True)
    document_template_id = Column(UUID, nullable=True)

    structured_plain = Column(String, nullable=True)

    summary = Column(String, nullable=True)

    user = relationship("UserDBO")

    @classmethod
    def apply_filters(self, fields, db: Session):
        filters = []

        if fields.get("id") is not None:
            filters.append(TranscriptionDBO.id == fields.get("id"))

        if fields.get("user_id") is not None:
            filters.append(TranscriptionDBO.user_id == fields.get("user_id"))

        if fields.get("date_begin"):
            date_begin = datetime.combine(
                datetime.strptime(fields.get("date_begin"), "%Y-%m-%d").date(), time.min
            ) + timedelta(hours=3)
        else:
            date_begin = datetime.min

        if fields.get("date_end"):
            date_end = datetime.combine(
                datetime.strptime(fields.get("date_end"), "%Y-%m-%d").date(), time.max
            ) + timedelta(hours=3)
        else:
            date_end = datetime.now()

        if fields.get("date_begin") or fields.get("date_end"):
            filters.append(
                TranscriptionDBO.transcription_date.between(date_begin, date_end)
            )

        if fields.get("doctor_id") is not None:
            filters.append(TranscriptionDBO.doctor_id == fields.get("doctor_id"))

        if fields.get("patient_cpf") is not None:
            filters.append(TranscriptionDBO.patient_cpf == fields.get("patient_cpf"))

        if fields.get("order_by") is not None:
            if fields.get("order_by") == "asc":
                return (
                    db.query(TranscriptionDBO)
                    .filter(*filters)
                    .order_by(TranscriptionDBO.transcription_date.asc())
                )

        return (
            db.query(TranscriptionDBO)
            .filter(*filters)
            .order_by(TranscriptionDBO.transcription_date.desc())
        )
