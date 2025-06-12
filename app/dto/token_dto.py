from typing import Union
from pydantic import BaseModel


class TokenDTO(BaseModel):
    access_token: str
    token_type: str

# Modelo para o Token de Dados
class TokenData(BaseModel):
    username: Union[str, None] = None