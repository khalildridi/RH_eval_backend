# from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
# from app.schemas.referentiel import ReferentielCreate, ReferentielOut, CompetenceCreate, CompetenceOut
# from app.core.security import verify_token
# from app.db.mongodb import get_db
# from app.utils.import_csv import import_referentiel_csv
# from app.models.referentiel import Referentiel, Competence
# from typing import List

# router = APIRouter()

# @router.post("/referentiels/", response_model=ReferentielOut)
# async def create_referentiel(referentiel: ReferentielCreate, current_user: dict = Depends(verify_token)):
#     if current_user["role"] not in ["GLOBAL_ADMIN", "RH_ADMIN"]:
#         raise HTTPException(status_code=403)
#     db = await get_db()
#     ref_dict = referentiel.dict()
#     ref_dict["tenant_id"] = current_user.get("tenant_id", "default")
#     result = await db.referentiels.insert_one(ref_dict)
#     ref_dict["id"] = str(result.inserted_id)
#     return ref_dict

# @router.post("/referentiels/import/")
# async def import_referentiel(file: UploadFile = File(...), current_user: dict = Depends(verify_token)):
#     if current_user["role"] not in ["GLOBAL_ADMIN", "RH_ADMIN"]:
#         raise HTTPException(status_code=403)
#     # Sauvegarde temporaire du fichier
#     file_path = f"/tmp/{file.filename}"
#     with open(file_path, "wb") as buffer:
#         buffer.write(await file.read())
#     result = await import_referentiel_csv(file_path, current_user.get("tenant_id", "default"))
#     return result

# @router.get("/competences/", response_model=List[CompetenceOut])
# async def list_competences(referentiel_id: str = None, current_user: dict = Depends(verify_token)):
#     db = await get_db()
#     query = {"tenant_id": current_user.get("tenant_id", "default")}
#     if referentiel_id:
#         query["referentiel_id"] = referentiel_id
#     competences = await db.competences.find(query).to_list(length=1000)
#     for c in competences:
#         c["id"] = str(c["_id"])
#         del c["_id"]
#     return competences

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from app.core.security import verify_token
from app.db.mongodb import get_db
# 🌟 Importation du nouvel utilitaire de parsing
from app.utils.import_referentiel import parse_referentiel_file
from typing import Dict, Any, List, Optional
from bson import ObjectId
from pydantic import BaseModel

router = APIRouter(prefix="/referentiel", tags=["referentiel"])

# ──────────────────────────────────────
# MODELS (pour validation Pydantic)
# ──────────────────────────────────────

# Modèle pour l'objet "niveaux" imbriqué
class CompetenceNiveaux(BaseModel):
    n1: Optional[str] = None
    n2: Optional[str] = None
    n3: Optional[str] = None
    n4: Optional[str] = None
    n5: Optional[str] = None # Ajout d'un N5 au cas où

# Modèle de base pour une compétence (utilisé pour la création)
class CompetenceBase(BaseModel):
    refComp: str
    domaine: str
    axe: str
    categorie: str
    nom: str
    definition: str
    niveaux: CompetenceNiveaux
    niveauAttendu: Optional[int] = None
    norme: Optional[str] = None
    
# Modèle pour les données retournées par l'API (avec ID)
class CompetenceResponse(CompetenceBase):
    id: str


# ──────────────────────────────────────
# ENDPOINT 1: GET /referentiel
# (Correspond à `fetchCompetences`)
# ──────────────────────────────────────
@router.get("/", response_model=List[CompetenceResponse])
async def list_competences(
    # current_user: dict = Depends(verify_token)
):
    db = await get_db()
    tenant_id = "default" # current_user.get("tenant_id", "default")
    query = {"tenant_id": tenant_id}
    
    competences_cursor = await db.referentiel.find(query).to_list(2000)
    
    # Formattage pour correspondre à CompetenceResponse
    response_list = []
    for comp in competences_cursor:
        comp_data = {
            **comp,
            "id": str(comp["_id"]),
        }
        # Gérer le cas où 'niveaux' n'est pas un dict (ancienne donnée)
        if not isinstance(comp_data.get("niveaux"), dict):
            comp_data["niveaux"] = {}
            
        response_list.append(CompetenceResponse(**comp_data))
        
    return response_list


# ──────────────────────────────────────
# ENDPOINT 2: POST /referentiel/preview
# (Correspond à `previewImportReferentiel`)
# ──────────────────────────────────────
@router.post("/preview", response_model=List[CompetenceBase])
async def preview_import(
    file: UploadFile = File(...),
    # current_user: dict = Depends(verify_token)
):
    # if current_user["role"] not in ["GLOBAL_ADMIN", "RH_ADMIN"]:
    #     raise HTTPException(status_code=403, detail="Accès refusé")
        
    if not file.filename.endswith(('.csv', '.xlsx')):
        raise HTTPException(status_code=400, detail="Format de fichier invalide. Utilisez CSV ou XLSX.")

    file_path = f"/tmp/{file.filename}"
    try:
        # Écrire le fichier temporairement
        with open(file_path, "wb") as f:
            f.write(await file.read())
        
        # 🌟 Appel de l'utilitaire de parsing
        parsed_data = await parse_referentiel_file(file_path)
        
        # Valider les données parsées avec Pydantic
        validated_data = [CompetenceBase(**item) for item in parsed_data]
        
        return validated_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'analyse du fichier: {str(e)}")


# ──────────────────────────────────────
# ENDPOINT 3: POST /referentiel/import
# (Correspond à `confirmImportReferentiel`)
# ──────────────────────────────────────
@router.post("/import", response_model=List[CompetenceResponse], status_code=status.HTTP_201_CREATED)
async def confirm_import(
    competences_to_import: List[CompetenceBase],
    # current_user: dict = Depends(verify_token)
):
    # if current_user["role"] not in ["GLOBAL_ADMIN", "RH_ADMIN"]:
    #     raise HTTPException(status_code=403, detail="Accès refusé")

    db = await get_db()
    tenant_id = "default" # current_user.get("tenant_id", "default")
    
    created_competences = []
    
    for comp_data in competences_to_import:
        # Vérifier l'unicité sur refComp + tenant_id
        existing = await db.referentiel.find_one({
            "refComp": comp_data.refComp,
            "tenant_id": tenant_id
        })
        
        if existing:
            # Optionnel: Mettre à jour l'existant ou ignorer.
            # Pour l'instant, nous ignorons les doublons.
            continue
            
        # Créer le document
        doc_to_insert = {
            **comp_data.dict(),
            "tenant_id": tenant_id,
            "created_at": ObjectId().generation_time,
        }
        
        result = await db.referentiel.insert_one(doc_to_insert)
        
        # Récupérer le doc créé et le formater pour la réponse
        new_doc = await db.referentiel.find_one({"_id": result.inserted_id})
        new_doc_response = CompetenceResponse(
            **new_doc,
            id=str(new_doc["_id"])
        )
        created_competences.append(new_doc_response)

    # Retourner uniquement les compétences qui ont été créées
    return created_competences