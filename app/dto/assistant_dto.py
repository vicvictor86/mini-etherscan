from datetime import datetime
from typing import Union
from pydantic import BaseModel

from app.utils.enums import TypeOfStructure


class AssistantDTO(BaseModel):
    id: int
    value: Union[str, None] = None
    transcription_type: TypeOfStructure
    created_at: datetime
