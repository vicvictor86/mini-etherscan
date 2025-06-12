import json
from passlib.context import CryptContext
from fastapi import HTTPException

# Configuração de hashing de senha
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configurar a conexão com o banco de dados
def get_password_hash(password):
    return pwd_context.hash(password)

# Função para verificar a senha
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def dbo_as_dict(instance):
    return {c.name: getattr(instance, c.name) for c in instance.__table__.columns}

def extract_json(string):
    json_objects = []
    start_index = string.find('{')
    while start_index != -1:
        end_index = string.find('}', start_index)
        if end_index != -1:
            json_str = string[start_index:end_index + 1]
            try:
                json_obj = json.loads(json_str)
                json_objects.append(json_obj)
            except json.JSONDecodeError:
                pass
            start_index = string.find('{', end_index)
        else:
            break
    return json_objects

def validate_json(text):
    if isinstance(text, dict):
        return text
    try:
        if isinstance(text, str):
            return json.loads(text)
    except Exception as e:
        response = json.loads(extract_json(str(text)))
        return response
    
def extract_json_from_string(texto):
    """
    Extrai um objeto JSON de um texto.
    
    Args:
        texto (str): O texto que contém um objeto JSON.
    
    Returns:
        dict or None: O objeto JSON extraído ou None se não houver JSON válido.
    """
    start = -1
    end = -1
    stack = []

    for i, char in enumerate(texto):
        if char == '{':
            if not stack:
                start = i
            stack.append(char)
        elif char == '}':
            stack.pop()
            if not stack:
                end = i + 1
                break

    if start != -1 and end != -1:
        json_str = texto[start:end]
        try:
            json_obj = json.loads(json_str)
            return json_obj
        except json.JSONDecodeError:
            return None
    return None

def format_json(data, indent=0):
    formatted_str = ""
    for key, value in data.items():
        if isinstance(value, dict):
            formatted_str += " " * indent + f"{key}:\n"
            formatted_str += format_json(value, indent + 2)
        elif isinstance(value, list):
            formatted_str += " " * indent + f"{key}:\n"
            for item in value:
                if isinstance(item, dict):
                    formatted_str += format_json(item, indent + 2)
                else:
                    formatted_str += " " * (indent + 2) + str(item) + "\n"
        else:
            formatted_str += " " * indent + f"{key}: {value}\n"
    return formatted_str

def audio_format_validator(audio_file):
    if not audio_file.filename.endswith(('.flac', '.m4a', '.mp3', '.mp4', '.mpeg', '.mpga', '.oga', '.ogg', '.wav', '.webm')):
        raise HTTPException(status_code=400, detail="Formato '{audio_file.content_type}' de arquivo não suportado. Formatos aceitos 'flac', 'm4a', 'mp3', 'mp4', 'mpeg', 'mpga', 'oga', 'ogg', 'wav', 'webm'.")
    
def identify_audio_format(data: bytes) -> str:
    """
    Identifica o formato de áudio a partir dos primeiros bytes do pacote de dados.
    
    :param data: Os bytes do primeiro pacote que contêm o header do arquivo de áudio.
    :return: Uma string indicando o formato do áudio (wav, webm, ogg, mp3) ou "unknown" se não identificado.
    """
    if len(data) < 12:
        return "unknown"  # Não há bytes suficientes para identificar o formato

    # Verificar se é WAV (Primeiros 4 bytes 'RIFF' e 8 a 12 'WAVE')
    if data[:4] == b'RIFF' and data[8:12] == b'WAVE':
        return "wav"

    # Verificar se é MP3 (Primeiro byte é 0xFF e bits de sincronização no segundo byte)
    if data[0] == 0xFF and (data[1] & 0xE0) == 0xE0:
        return "mp3"

    # Verificar se é OGG (Primeiros 4 bytes 'OggS')
    if data[:4] == b'OggS':
        return "ogg"

    # Verificar se é WebM (Arquivos WebM começam com os primeiros 4 bytes '1A 45 DF A3')
    if data[:4] == b'\x1A\x45\xDF\xA3':
        return "webm"

    # Se nenhum formato foi identificado
    return "unknown"