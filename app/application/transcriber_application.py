from sqlalchemy.orm.attributes import flag_modified
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc
import traceback
import time
import json
import os

from app.application.clients.assistant_methods import (
    appointment_assistant,
    ask_to_prompt,
)
from app.application.aws_application import generate_presigned_url, upload_file

from app.dto.reviewed_response import ReviewedResponse as reviewed_response_dto
from app.dto.transcription_dto import TranscriptionResponse
from app.dbo.transcription_dbo import TranscriptionDBO
from app.dto.user_dto import UserDTO

from app.utils.functions import extract_json_from_string, validate_json, format_json
from app.utils.embedding_text import embedding_and_save_text, embedding_text
from app.utils.audio_utils import retrieve_audio_duration
from app.utils.loggers import logger, error_logger
from app.utils.enums import Language, UserRole
from app.utils.pricing_utils import (
    calculate_structure_cost,
    calculate_transcription_cost,
)


def transcribe_and_structure(
    background_tasks: BackgroundTasks,
    audio_file,
    current_user,
    patient_name,
    patient_cpf,
    patient_phone,
    doctor_id,
    transcription_text,
    form_schema,
    document_template_id,
    language: Language | None = Language.pt,
    db: Session | None = None,
):
    logger.info(f"Transcribing and structuring text: {transcription_text}")
    start_time = time.time()

    request_date = datetime.now(timezone.utc)
    url_audio = None
    audio_duration = 0
    if audio_file is not None:
        original_filename = audio_file.filename.split(".")[0]
        audio_file.filename = (
            f"{original_filename}_{doctor_id}_{patient_cpf}_{request_date.strftime('%Y%m%d%H%M%S')}."
            + audio_file.filename.split(".")[-1]
        )

        # Read the file bytes and return to the start to be upload on the bucket
        audio_content = audio_file.file.read()
        audio_file.file.seek(0)

        upload_file(audio_file)
        url_audio = audio_file.filename

        audio_duration = retrieve_audio_duration(audio_content)
    logger.info(f"Time taken to upload file: {time.time() - start_time} seconds")

    request_date = datetime.now(timezone.utc)

    input_tokens = 0
    output_tokens = 0
    structure_model = "gpt-4o-mini"
    try:
        transcriber_response = {
            "dialyzed_transcript": {},
            "raw_transcript": transcription_text,
        }

        form_schema = str(form_schema).replace("'", '"')

        message = (
            "<TRANSCRIPTION>"
            + transcriber_response["raw_transcript"]
            + "</TRANSCRIPTION>"
            + "\n"
            + "<SCHEMA>"
            + form_schema
            + "</SCHEMA>"
        )

        assistant_response_tokens_quantity = appointment_assistant(message, language)

        gpt_response = assistant_response_tokens_quantity["assistant_response"]

        input_tokens = assistant_response_tokens_quantity["prompt_token"]
        output_tokens = assistant_response_tokens_quantity["completion_token"]
        structure_model = assistant_response_tokens_quantity["model"]

        gpt_response = extract_json_from_string(gpt_response)
        if not gpt_response:
            error_logger.error(
                f"Erro não tratado: {str(e)}\n"
                f"Stack trace:\n{traceback.format_exc()}"
            )
            raise HTTPException(
                status_code=500,
                detail="Não foi possível estruturar a resposta da solicitação, consulte um administrador do sistema.",
            )

        response = {
            "status_code": 200,
            "raw": transcriber_response["raw_transcript"],
            "structured_json": gpt_response,
        }
    except Exception as e:
        error_logger.error(
            f"Erro não tratado: {str(e)}\n" f"Stack trace:\n{traceback.format_exc()}"
        )
        raise HTTPException(
            status_code=500,
            detail="Não foi possível estruturar a resposta da solicitação, consulte um administrador do sistema.",
        )

    structured_str = validate_json(gpt_response)
    structured_plain = format_json(structured_str)

    summary = ask_to_prompt(transcription_text, "summary", language=language)

    service = os.getenv("ASSISTANT_PROVIDER")
    structure_cost = calculate_structure_cost(
        service=service,
        model=structure_model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
    transcription_cost = calculate_transcription_cost("azure", audio_duration)

    new_transcription = TranscriptionDBO(
        user_id=current_user.id,
        patient_name=patient_name,
        patient_cpf=patient_cpf,
        patient_phone=patient_phone,
        doctor_id=doctor_id,
        audio_url=url_audio,
        document_template_id=document_template_id,
        raw_transcription=transcriber_response["raw_transcript"],
        structured_plain=structured_plain,
        transcription_date=request_date,
        response_json=response,
        summary=summary,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        structure_model=structure_model,
        structure_cost=structure_cost["total_cost"],
        transcription_cost=transcription_cost["total_cost"],
        audio_duration_in_seconds=audio_duration,
    )

    db.add(new_transcription)
    db.commit()
    db.refresh(new_transcription)

    background_tasks.add_task(
        embedding_and_save_text,
        structured_plain,
        new_transcription.id,
        db,
    )

    response["transcription_id"] = new_transcription.id

    return response


def get_transcription_v2(transcription_id: int, db: Session | None = None):
    try:
        transcription = (
            db.query(TranscriptionDBO)
            .filter(
                TranscriptionDBO.id == transcription_id,
            )
            .order_by(desc(TranscriptionDBO.transcription_date))
            .first()
        )

    except Exception as e:
        error_logger.error(
            f"Erro não tratado: {str(e)}\n" f"Stack trace:\n{traceback.format_exc()}"
        )
        return HTTPException(
            status_code=503,
            detail="Erro ao buscar transcrição. Tente novamente mais tarde.",
        )
    if transcription is None:
        raise HTTPException(
            status_code=404, detail="Transcrição não encontrada para esses ids."
        )
    if transcription.response_json is None:
        raise HTTPException(
            status_code=404, detail="Emprocessamento, tente novamente mais tarde."
        )

    return transcription.response_json


def get_transcription_by_filter(requests_filter_schema, db: Session):
    filtered = TranscriptionDBO.apply_filters(requests_filter_schema, db)
    transcription = filtered.first()

    if transcription is None:
        raise HTTPException(
            status_code=404,
            detail="Transcrição não encontrada para esse id e esse usuário.",
        )
    transcription = TranscriptionResponse.model_validate(transcription)

    transcription_return = dict(transcription)
    transcription_return["response"] = transcription.response_json
    del transcription_return["response_json"]

    return transcription_return


def get_audio_presigned_url(
    transcription_id: int,
    current_user: UserDTO | None = None,
    db: Session | None = None,
):
    logger.info("Gerando URL presignada para o áudio")
    transcription = (
        db.query(TranscriptionDBO)
        .filter(TranscriptionDBO.id == transcription_id)
        .order_by(desc(TranscriptionDBO.id))
        .first()
    )
    if transcription is None:
        raise HTTPException(
            status_code=404, detail="Transcrição não encontrada para esses ids."
        )
    elif transcription.audio_url is None:
        raise HTTPException(
            status_code=404, detail="Áudio não encontrado para essa transcrição."
        )
    presigned_url = generate_presigned_url(transcription.audio_url)
    logger.info("URL presignada gerada com sucesso")
    logger.info("{presigned_url}")

    if presigned_url:
        if current_user.role == UserRole.admin:
            return {"status_code": 200, "presigned_url": presigned_url}
        elif current_user.role == UserRole.consultant:
            if transcription.transcription_date + timedelta(
                days=7
            ) > datetime.now().replace(tzinfo=None):
                return {"status_code": 200, "presigned_url": presigned_url}
    raise HTTPException(status_code=403, detail="Acesso negado. O áudio expirou.")


def save_reviewed_response(
    reviewed: reviewed_response_dto,
    current_user: UserDTO | None = None,
    db: Session | None = None,
):

    if not reviewed.reviewed_response:
        raise HTTPException(
            status_code=400,
            detail="Erro ao salvar a resposta. O JSON não pode ser vazio.",
        )

    logger.info("Save reviewed response call made")

    if reviewed.transcription_id is None:
        raise HTTPException(
            status_code=400, detail="Erro ao salvar a resposta. Parâmetros inválidos."
        )

    transcription = (
        db.query(TranscriptionDBO)
        .filter(TranscriptionDBO.id == reviewed.transcription_id)
        .order_by(desc(TranscriptionDBO.id))
        .first()
    )

    if transcription is None or transcription.response_json is None:
        raise HTTPException(
            status_code=404, detail="Transcrição não encontrada para o id informado."
        )
    if transcription.user_id != current_user.id:
        logger.error("Acesso negado")
        raise HTTPException(
            status_code=403,
            detail="Acesso negado. Você não tem permissão para editar essa transcrição.",
        )

    if reviewed.reviewed_response:
        try:
            transcription.response_json["structured_json"] = reviewed.reviewed_response
            flag_modified(transcription, "response_json")

            structured_str = validate_json(reviewed.reviewed_response)
            structured_plain = format_json(structured_str)

            structured_plain_embedded = embedding_text(structured_plain)

            transcription.reviewed_response_json = reviewed.reviewed_response

            transcription.structured_plain = structured_plain
            transcription.structured_plain_embedded = structured_plain_embedded

            db.commit()
        except json.JSONDecodeError as e:
            print(f"Erro ao decodificar JSON: {e}")
            print(f"Conteúdo problemático: {transcription.response_json}")
            logger.error(
                f"Save reviewed response call ended unsuccessfully: {e} response content: {transcription.response_json}"
            )
            raise HTTPException(
                status_code=400, detail="Erro ao processar a resposta revisada."
            )
        except Exception as e:
            print(f"Erro inesperado: {e}")
            logger.error(
                f"Save reviewed response call ended unsuccessfully: {e} response content: {transcription.response_json}"
            )
            raise HTTPException(
                status_code=500, detail="Erro ao salvar a resposta revisada."
            )

    logger.info("Save reviewed response call ended sucessfully")


def excluir_transcription(
    transcription_id: int,
    current_user: UserDTO | None = None,
    db: Session | None = None,
):
    transcription = (
        db.query(TranscriptionDBO)
        .filter(TranscriptionDBO.id == transcription_id)
        .order_by(desc(TranscriptionDBO.id))
        .first()
    )

    if transcription is None:
        raise HTTPException(
            status_code=404, detail="Transcrição não encontrada para esses ids."
        )

    if transcription.user_id == current_user.id or current_user.role == UserRole.admin:
        db.delete(transcription)
        db.commit()

        return {"status_code": 200, "message": "Transcrição excluída com sucesso."}

    raise HTTPException(
        status_code=403,
        detail="Acesso negado. Você não tem permissão para excluir essa transcrição",
    )
