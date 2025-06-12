from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from sqlalchemy.orm import Session
import json

from app.dto.pagination_params import PaginationParams
from app.dto.transcription_dto import (
    TranscriptionHistoryResponse,
    TranscriptionsQueryParams,
    Transcription_request,
)
from app.application.transcriber_application import (
    transcribe_and_structure,
    excluir_transcription,
    get_transcription_v2,
    get_transcription_by_filter,
    get_audio_presigned_url,
)
from app.auth_middleware import get_current_active_user
from app.dto.user_dto import UserDTO
from app.dbo.transcription_dbo import TranscriptionDBO
from app.utils.enums import Language, UserRole
from app.database import get_db


file_supported = "Arquivo de áudio. Aceita apenas os formatos: .mp3, .mp4, .opus, .ogg"

router = APIRouter(
    prefix="/transcriber",
    tags=["Med Ai Transcriber"],
    dependencies=[Depends(get_current_active_user)],
    responses={404: {"description": "Not found"}},
)


@router.post("/transcribe_appointment", summary="Summarize audio from appointment.")
async def transcribe_appointment(
    background_tasks: BackgroundTasks,
    transcriber_request: str = Form(
        ...,
        examples=[
            """{
            "doctor_id": "123e4567-e89b-12d3-a456-426614174000",
            "patient_name": "John Doe",
            "patient_cpf": "123.456.789-00",
            "patient_phone": "(11) 99999-9999",
            "transcription_text": "Patient consultation notes...",
            "document_template_id": "123e4567-e89b-12d3-a456-426614174000",
            "form_schema": {"field1": "value1", "field2": "value2"}
        }"""
        ],
    ),
    audio_file: UploadFile = File(None, description=file_supported),
    current_user: UserDTO = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    # Parse o JSON string para dict
    transcriber_data = json.loads(transcriber_request)
    # Valide com seu modelo Pydantic
    try:
        validated_request = Transcription_request(**transcriber_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # audio_format_validator(audio_file)

    response = transcribe_and_structure(
        background_tasks=background_tasks,
        audio_file=audio_file,
        current_user=current_user,
        document_template_id=validated_request.document_template_id,
        transcription_text=validated_request.transcription_text,
        doctor_id=validated_request.doctor_id,
        patient_name=validated_request.patient_name,
        patient_cpf=validated_request.patient_cpf,
        patient_phone=validated_request.patient_phone,
        form_schema=validated_request.form_schema,
        language=validated_request.language,
        db=db,
    )
    return response


@router.delete(
    "/delete_transcription", summary="Delete the transcription of an appointment."
)
def delete_transcription(
    transcription_id: int,
    current_user: UserDTO = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):

    response = excluir_transcription(
        current_user=current_user, transcription_id=transcription_id, db=db
    )
    return response


@router.get(
    "/retrieve_appointment", summary="Retrieves the transcription of an appointment."
)
def transcriber_appointment(
    transcription_id: int,
    current_user: UserDTO = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):

    response = get_transcription_v2(transcription_id=transcription_id, db=db)
    return response


@router.get(
    "/transcriptions_history/{page}/{per_page}", summary="Retrieves all transcriptions."
)
def get_transcriptions_history(
    pagination: PaginationParams = Depends(),
    query_params: TranscriptionsQueryParams = Depends(),
    current_user: UserDTO = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    offset = (pagination.page - 1) * pagination.per_page

    requests_filter_schema = query_params.dict()
    if current_user.role != UserRole.admin.value:
        requests_filter_schema["user_id"] = current_user.id

        if not query_params.doctor_id:
            raise HTTPException(status_code=400, detail="doctor_id is required.")

    filtered = TranscriptionDBO.apply_filters(requests_filter_schema, db)
    transcriptions = filtered.offset(offset).limit(pagination.per_page).all()

    if query_params.doctor_id:
        for transcription in transcriptions:
            if transcription.doctor_id != query_params.doctor_id:
                raise HTTPException(
                    status_code=400,
                    detail="doctor_id does not match with the transcriptions.",
                )

    requests_formatted = [
        TranscriptionHistoryResponse.model_validate(item) for item in transcriptions
    ]

    return {
        "total": filtered.count(),
        "requests": requests_formatted,
    }


@router.get(
    "/transcription_by_id/{transcription_id}", summary="Retrieves transcription by id."
)
def transcription_by_id(
    transcription_id: int = 0,
    current_user: UserDTO = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):

    requests_filter_schema = {"id": transcription_id}
    if current_user.role != UserRole.admin.value:
        requests_filter_schema["user_id"] = current_user.id

    transcription = get_transcription_by_filter(requests_filter_schema, db=db)

    return transcription


@router.get(
    "/get_audio_presigned/", summary="Retrieves the pre-signed URL of the audio."
)
def get_audio_url(
    transcription_id: int,
    current_user: UserDTO = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    requests_filter_schema = {"id": transcription_id}
    if current_user.role != UserRole.admin.value:
        requests_filter_schema["user_id"] = current_user.id

    get_transcription_by_filter(requests_filter_schema, db=db)

    return get_audio_presigned_url(
        transcription_id=transcription_id, current_user=current_user, db=db
    )
