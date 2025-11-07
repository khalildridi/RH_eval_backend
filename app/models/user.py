from pydantic import BaseModel
from typing import Optional
from bson import ObjectId

class User(BaseModel):
    id: Optional[str] = None  # _id en str pour JSON
    nom: str
    prenom: str
    email: str
    password_hash: str
    role: str  # GLOBAL_ADMIN, RH_ADMIN, MANAGER, COLLABORATEUR
    department: Optional[str] = None
    manager_id: Optional[str] = None
    tenant_id: str
    statut: str = "actif"

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}