from beanie import Document, PydanticObjectId
from pydantic import Field, EmailStr
from datetime import datetime
from typing import Optional
from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    ENGINEER = "engineer"


class UserStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    REJECTED = "rejected"
    INACTIVE = "inactive"


class User(Document):
    email: EmailStr
    password_hash: str
    role: UserRole = UserRole.ENGINEER
    full_name: str
    status: UserStatus = UserStatus.PENDING
    approved_by: Optional[PydanticObjectId] = None
    approved_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"
        indexes = ["email", "status"]