from sqlalchemy import Boolean, Column, Integer, Sequence, String
from app.database import Base
from sqlalchemy.orm import Session


class UserDBO(Base):
    __tablename__ = "users"
    id = Column(Integer, Sequence("user_id_seq"), primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(100), nullable=False)
    disabled = Column(Boolean, default=False)
    role = Column(String(100), nullable=False)


def get_user(username: str, db: Session):
    return db.query(UserDBO).filter(UserDBO.username == username).first()
