from pydantic import BaseModel, EmailStr
from typing import Optional

class UserBase(BaseModel):
    email: EmailStr
    nom: str
    prenom: str

class UserCreate(UserBase):
    password: str
    role: str  # GLOBAL_ADMIN, RH_ADMIN, MANAGER, COLLABORATEUR
    department: Optional[str] = None
    tenant_id: str = "default"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(UserBase):
    id: str
    role: str
    department: Optional[str] = None
    tenant_id: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"