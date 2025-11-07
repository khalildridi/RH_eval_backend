from pydantic import BaseModel
from typing import List, Optional, Literal
from datetime import datetime

class CampagneCreate(BaseModel):
    nom: str
    description: str
    date_debut: datetime
    date_fin: datetime
    referentiel_id: str
    fiches_incluses: List[str]  # IDs des fiches de fonction

class CampagneOut(CampagneCreate):
    id: str
    statut: Literal["brouillon", "en_cours", "terminee"] = "brouillon"
    tenant_id: str