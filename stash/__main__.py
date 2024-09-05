import base64
import pathlib
import traceback

import cryptography
import cryptography.exceptions
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from fastapi import Depends, FastAPI, HTTPException, Request, staticfiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import OAuth2PasswordBearer
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from . import crud, models, schemas
from .database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

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
    return templates.TemplateResponse("index.html", {"request": request})


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
    token: str | None = Depends(oauth2_scheme),
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
