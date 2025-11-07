from pydantic import BaseModel
from typing import Literal, Optional, Dict

class Niveaux(BaseModel):
    N1: str
    N2: str
    N3: str
    N4: str

class CompetenceCreate(BaseModel):
    ref_comp: str
    ref_ff: str
    domaine: str
    axe: str
    categorie: str
    definition: str
    niveaux: Niveaux
    niveau_attendu: Optional[Literal["N1", "N2", "N3", "N4"]] = "N2"

class CompetenceOut(CompetenceCreate):
    id: str
    referentiel_id: str
    tenant_id: str

class ReferentielCreate(BaseModel):
    nom: str
    type: str  # commun, specifique

class ReferentielOut(ReferentielCreate):
    id: str
    tenant_id: str