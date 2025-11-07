from pydantic import BaseModel
from typing import Optional, Dict, Any
from bson import ObjectId

class Competence(BaseModel):
    id: Optional[str] = None
    ref_comp: str
    ref_ff: str
    domaine: str
    axe: str
    categorie: str
    definition: str
    niveaux: Dict[str, str]  # {"N1": desc, ...}
    niveau_attendu: str = "N2"
    referentiel_id: str
    tenant_id: str

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class Referentiel(BaseModel):
    id: Optional[str] = None
    nom: str
    type: str  # commun, specifique
    tenant_id: str

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}