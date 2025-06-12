from fastapi import HTTPException
from app.dbo.user_dbo import UserDBO
from app.dto.user_dto import UserCreate, UserUpdate
from app.utils.functions import get_password_hash
from sqlalchemy.orm import Session

def insert_user(
        user: UserCreate,
        db: Session
        ):
    
    hashed_password = get_password_hash(user.password)
    try:
        db_user = UserDBO(username=user.username, hashed_password=hashed_password, full_name=user.full_name, email=user.email, role=user.role)
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
    except Exception as e:
        db.rollback()
        raise e
    return db_user

def get_users(db: Session):
    try:
        db_users = db.query(UserDBO).all()
    except Exception as e:
        db.rollback()
        raise e
    return db_users

def update_user(
        user_id: int, 
        user: UserUpdate,
        db: Session
        ):
    db_user = db.query(UserDBO).filter(UserDBO.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if user.username:
        db_user.username = user.username
    if user.password:
        db_user.hashed_password = get_password_hash(user.password)
    if user.full_name:
        db_user.full_name = user.full_name
    if user.email:
        db_user.email = user.email
    if user.role:
        db_user.role = user.role
    db.commit()
    db.refresh(db_user)
    
    return db_user

def delete_user(
        user_id: int,
        db: Session
        ):
    db_user = db.query(UserDBO).filter(UserDBO.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    db.delete(db_user)
    db.commit()
    return {"detail": f"Usuário '{db_user.username}' deletado com sucesso"}
    