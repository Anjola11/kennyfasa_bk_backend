

from sqlmodel import SQLModel, Field, Column
import uuid
from datetime import datetime, timezone
import sqlalchemy.dialects.postgresql as pg

from enum import Enum


def utc_now():
   
    return datetime.now(timezone.utc)

class Role(str, Enum):
    STAFF = "staff"
    ADMIN = "admin"

class User(SQLModel, table=True):
    __tablename__ = "users"
    
    user_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    username: str
    full_name: str
    password_hash: str = Field(exclude=True)
    role: Role
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(pg.TIMESTAMP(timezone=True))
    )
