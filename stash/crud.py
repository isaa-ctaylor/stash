import random
import string

import bcrypt
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models, schemas


def get_user(db: Session, user_id: int) -> models.User:
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> models.User:
    return db.query(models.User).filter(models.User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> list[models.User]:
    return db.query(models.User).offset(skip).limit(limit).all()


def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(user.password.encode("utf-8"), salt)

    db_user = models.User(
        email=user.email, hashed_password=hashed_password, is_admin=user.is_admin
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_stashes(db: Session, skip: int = 0, limit: int = 100) -> list[models.Stash]:
    return db.query(models.Stash).offset(skip).limit(limit).all()


def get_ids(db: Session, skip: int = 0, limit: int = 100) -> list[str]:
    return db.query(models.Stash.id).offset(skip).limit(limit).all()


def generate_random_string(length: int) -> str:
    letters = string.ascii_letters
    return "".join(random.choice(letters) for _ in range(length))


def create_stash(db: Session, stash: schemas.StashCreate, user_id: str) -> models.Stash:
    current_ids = get_ids(db)
    while (id := generate_random_string(length=6)) in current_ids:
        pass
    db_stash = models.Stash(id=id, **stash.model_dump(), owner_id=user_id)
    db.add(db_stash)
    db.commit()
    db.refresh(db_stash)
    return db_stash
