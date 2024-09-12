import base64
import datetime
import os
import pathlib

import bcrypt
import cryptography
import cryptography.exceptions
import jwt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, Security, staticfiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import (
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm,
    SecurityScopes,
)
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session

from . import crud, models, schemas
from .database import SessionLocal, engine

load_dotenv()

__version__ = "0.0.1"

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

oauth_scheme = OAuth2PasswordBearer(
    tokenUrl="token",
    auto_error=False,
    scopes={
        "me": "Read information about the current user.",
    },
)
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRES_MINUTES = 30
CREDENTIALS_EXCEPTION = HTTPException(
    status_code=401,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

wd = pathlib.Path(__file__).parent.resolve()

templates = Jinja2Templates(directory=wd / "templates")

app.mount(
    "/scripts",
    staticfiles.StaticFiles(directory=wd / "static/dist/js/"),
    name="scripts",
)
app.mount(
    "/styles",
    staticfiles.StaticFiles(directory=wd / "static/dist/css/"),
    name="styles",
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse(
        "index.html", {"request": request, "version": __version__}
    )


@app.get("/favicon.ico")
def favicon():
    return FileResponse(wd / "static/assets/favicon.ico")


@app.exception_handler(404)
def not_found(request: Request, exc: HTTPException):
    return templates.TemplateResponse(
        "404.html", {"request": request, "detail": exc.detail}, status_code=404
    )


def get_key_from_password(password, salt):
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # 256 bits
        salt=salt,
        iterations=100000,
        backend=default_backend(),
    )
    return kdf.derive(password.encode())


def decrypt_string(encrypted_data, password):
    # Decode the base64 encoded string to get the combined buffer
    combined_buffer = base64.b64decode(encrypted_data)

    # Extract salt, iv, and ciphertext from the combined buffer
    salt = combined_buffer[:16]
    iv = combined_buffer[16:28]
    cipher_text_with_tag = combined_buffer[28:]

    # Extract the actual cipher text and tag
    cipher_text = cipher_text_with_tag[:-16]
    tag = cipher_text_with_tag[-16:]

    # Derive the key using the password and salt
    key = get_key_from_password(password, salt)

    # Decrypt the cipher text
    cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend())
    decryptor = cipher.decryptor()
    decrypted_text = decryptor.update(cipher_text) + decryptor.finalize()

    return decrypted_text.decode()


def get_stash_id_from_request(request: Request):
    stash_id = request.url.path.rstrip("/").rsplit("/", 1)[-1]
    return stash_id


def resolve_stash(
    request: Request,
    db: Session = Depends(get_db),
    token: str | None = Depends(oauth_scheme),
    stash_id: str = Depends(get_stash_id_from_request),
    raw: bool | None = None,
):
    stash = crud.get_stash_by_id(db, stash_id=stash_id)

    if stash:
        if stash.protected:
            if token:
                try:
                    stash.content = decrypt_string(stash.content, token)
                except cryptography.exceptions.InvalidTag as e:
                    raise HTTPException(status_code=401, detail="Invalid token")
            else:
                if raw:
                    raise HTTPException(status_code=401, detail="Invalid token")

        return stash

    raise HTTPException(status_code=404, detail="Page not found")


def decode_token(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth_scheme),
    db: Session = Depends(get_db),
):
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = "Bearer"
    try:
        payload: dict = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise CREDENTIALS_EXCEPTION
        token_scopes = payload.get("scopes", [])
        token_data = schemas.TokenData(username=username, scopes=token_scopes)
    except (jwt.InvalidTokenError, ValidationError):
        raise CREDENTIALS_EXCEPTION

    for scope in security_scopes.scopes:
        if scope not in token_data.scopes:
            raise HTTPException(
                status_code=401,
                detail="Not enough permissions",
                headers={"WWW-Authenticate": authenticate_value},
            )

    user = crud.get_user_by_email(db, email=token_data.username)
    return user


async def get_current_user(user: schemas.User | None = Depends(decode_token)):
    if not user:
        raise CREDENTIALS_EXCEPTION
    return user


async def get_current_active_user(
    current_user: schemas.User = Security(get_current_user, scopes=["me"]),
):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def create_access_token(data: dict, expires_delta: datetime.timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.now(datetime.timezone.utc) + expires_delta
    else:
        expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
            minutes=30
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@app.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user: models.User = crud.get_user_by_email(db, email=form_data.username)
    if not user:
        raise CREDENTIALS_EXCEPTION
    if not bcrypt.checkpw(bytes(form_data.password, "utf-8"), user.hashed_password):
        raise CREDENTIALS_EXCEPTION
    access_token_expires = datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRES_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "scopes": ["me"]},
        expires_delta=access_token_expires,
    )
    return schemas.Token(access_token=access_token, token_type="bearer")


@app.get("/admin")
def admin(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return "admin"


@app.get("/users/me")
async def read_users_me(
    current_user: models.User = Depends(get_current_active_user),
):
    return current_user


@app.get("/{stash_id}")
async def get_stash(
    stash_id: str,
    request: Request,
    stash: schemas.Stash | None = Depends(resolve_stash),
    raw: bool | None = None,
):
    if not stash:
        raise HTTPException(status_code=404, detail="Page not found")

    if raw:
        return JSONResponse({"content": stash.content})

    return templates.TemplateResponse(
        "stash.html",
        {
            "request": request,
            "stash_id": stash_id,
            "content": stash.content,
            "protected": stash.protected,
        },
    )


@app.post("/upload", response_model=schemas.Stash)
def create_item_for_user(stash: schemas.StashCreate, db: Session = Depends(get_db)):
    return crud.create_stash(db=db, stash=stash)


# @app.post("/users", response_model=schemas.User)
# def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
#     db_user = crud.get_user_by_email(db, email=user.email)
#     if db_user:
#         raise HTTPException(status_code=400, detail="Email already registered")
#     return crud.create_user(db=db, user=user)


# @app.get("/users", response_model=list[schemas.User])
# def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
#     users = crud.get_users(db, skip=skip, limit=limit)
#     return users


# @app.get("/users/{user_id}", response_model=schemas.User)
# def read_user(user_id: int, db: Session = Depends(get_db)):
#     db_user = crud.get_user(db, user_id=user_id)
#     if db_user is None:
#         raise HTTPException(status_code=404, detail="User not found")
#     return db_user
