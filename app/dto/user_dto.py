from typing import Union
from pydantic import BaseModel
from app.utils.enums import UserRole

class UserDTO(BaseModel):
    id: int
    username: str
    full_name: Union[str, None] = None
    email: Union[str, None] = None
    hashed_password: Union[str, None] = None
    disabled: Union[bool, None] = None
    role: UserRole
    
    def __repr__(self) -> str:
        return (f"UserDTO(id={self.id}, username={self.username}, full_name={self.full_name} email={self.email}, disabled={self.disabled}, role={self.role})")
    
class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str
    email: str
    role: UserRole
    
    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str
    email: str
    role: UserRole

class UserUpdate(BaseModel):
    username: Union[str, None] = None
    password: Union[str, None] = None
    full_name: Union[str, None] = None
    email: Union[str, None] = None
    role: Union[UserRole, None] = None