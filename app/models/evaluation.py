from pydantic import BaseModel
from typing import Optional, List
from bson import ObjectId

class DetailEvaluation(BaseModel):
    ref_comp: str
    niveau_attendu: str
    niveau_observe: Optional[str] = None
    ecart: Optional[int] = None  # Calculé : observe - attendu (N1=1, N2=2...)
    commentaire: str = ""

class Evaluation(BaseModel):
    id: Optional[str] = None
    campagne_id: str
    collaborateur_id: str
    manager_id: str
    details: List[DetailEvaluation]
    statut: str = "en_attente"  # en_attente, soumise, validée
    commentaires_collaborateur: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}