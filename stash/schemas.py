from pydantic import BaseModel


class StashBase(BaseModel):
    pass


class StashCreate(StashBase):
    content: str
    protected: bool = False
    salt: str


class Stash(StashBase):
    id: str
    content: str
    protected: bool = False
    salt: str
    owner_id: int

    class Config:
        from_attributes = True


class UserBase(BaseModel):
    email: str
    is_admin: bool = False


class UserCreate(UserBase):
    password: str
    is_admin: bool = False


class User(UserBase):
    id: int
    is_active: bool

    stashes: list[Stash] = []

    class Config:
        from_attributes = True
