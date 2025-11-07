# from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
# from app.core.security import verify_token
# from app.db.mongodb import get_db
# from app.utils.import_csv import import_collaborateurs_csv
# from typing import Dict, Any, List

# router = APIRouter()

# @router.post("/collaborateurs/import/")
# async def import_collaborateurs(file: UploadFile = File(...), current_user: dict = Depends(verify_token)):
#     if current_user["role"] not in ["GLOBAL_ADMIN", "RH_ADMIN"]:
#         raise HTTPException(status_code=403)
#     file_path = f"/tmp/{file.filename}"
#     with open(file_path, "wb") as buffer:
#         buffer.write(await file.read())
#     result = await import_collaborateurs_csv(file_path, current_user.get("tenant_id", "default"))
#     return result

# @router.get("/collaborateurs/", response_model=List[Dict[str, Any]])
# async def list_collaborateurs(current_user: dict = Depends(verify_token)):
#     db = await get_db()
#     collabs = await db.collaborateurs.find({"tenant_id": current_user.get("tenant_id", "default")}).to_list(length=1000)
#     for c in collabs:
#         c["id"] = str(c["_id"])
#         del c["_id"]
#     return collabs

# @router.post("/collaborateurs/{collab_id}/assign-fiche/{fiche_id}")
# async def assign_fiche(collab_id: str, fiche_id: str, current_user: dict = Depends(verify_token)):
#     if current_user["role"] not in ["GLOBAL_ADMIN", "RH_ADMIN"]:
#         raise HTTPException(status_code=403)
#     db = await get_db()
#     await db.collaborateurs.update_one({"_id": collab_id}, {"$set": {"fiche_fonction_id": fiche_id}})
#     return {"message": "Fiche assignée"}
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from app.core.security import verify_token
from app.db.mongodb import get_db
from app.utils.import_csv import import_collaborateurs_csv
from typing import Dict, Any, List, Optional
from bson import ObjectId
from pydantic import BaseModel
import re

router = APIRouter(prefix="/collaborateurs", tags=["collaborateurs"])


# ──────────────────────────────────────
# MODELS (pour validation)
# ──────────────────────────────────────
class CollaborateurCreate(BaseModel):
    civilite: str  # "M" | "Mme"
    prenom: str
    nom: str
    fonction: str
    refFF: str
    managerId: str
    direction: str
    departement: str
    email: str
    isManager: bool


class CollaborateurUpdate(BaseModel):
    civilite: Optional[str] = None
    prenom: Optional[str] = None
    nom: Optional[str] = None
    fonction: Optional[str] = None
    refFF: Optional[str] = None
    managerId: Optional[str] = None
    direction: Optional[str] = None
    departement: Optional[str] = None
    email: Optional[str] = None
    statut: Optional[str] = None  # "actif" | "archive"
    isManager:  Optional[bool] = None 


# ──────────────────────────────────────
# UTILS
# ──────────────────────────────────────
async def get_collab_or_404(db, collab_id: str, tenant_id: str):
    collab = await db.collaborateurs.find_one({"_id": ObjectId(collab_id), "tenant_id": tenant_id})
    if not collab:
        raise HTTPException(status_code=404, detail="Collaborateur non trouvé")
    collab["id"] = str(collab["_id"])
    del collab["_id"]
    return collab


def clean_search_term(term: str) -> str:
    return re.escape(term.strip().lower())


# ──────────────────────────────────────
# IMPORT CSV
# ──────────────────────────────────────
@router.post("/import/")
async def import_collaborateurs(
    file: UploadFile = File(...),
    current_user: dict = Depends(verify_token)
):
    if current_user["role"] not in ["GLOBAL_ADMIN", "RH_ADMIN"]:
        raise HTTPException(status_code=403, detail="Accès refusé")

    file_path = f"/tmp/{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())

    result = await import_collaborateurs_csv(file_path, current_user.get("tenant_id", "default"))
    return {"imported": result, "message": "Import réussi"}


# ──────────────────────────────────────
# LISTE + RECHERCHE (GET /collaborateurs)
# ──────────────────────────────────────
@router.get("/", response_model=List[Dict[str, Any]])
async def list_collaborateurs(
    search: Optional[str] = Query(None, description="Recherche par nom, email, refFF"),
    statut: Optional[str] = Query(None, description="Filtre: actif | archive"),
    # current_user: dict = Depends(verify_token)
):
    db = await get_db()
    tenant_id ="default"
    # current_user.get("tenant_id", "default")
    query = {"tenant_id": tenant_id}

    if statut in ["actif", "archive"]:
        query["statut"] = statut

    if search:
        search_clean = clean_search_term(search)
        regex = {"$regex": search_clean, "$options": "i"}
        query["$or"] = [
            {"prenom": regex},
            {"nom": regex},
            {"email": regex},
            {"refFF": regex},
        ]

    collabs = await db.collaborateurs.find(query).to_list(1000)
    for c in collabs:
        c["id"] = str(c["_id"])
        del c["_id"]
    return collabs


# ──────────────────────────────────────
# CRÉER UN COLLABORATEUR (POST /collaborateurs)
# Retourne l'objet complet au lieu de juste l'ID
# ──────────────────────────────────────
@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_collaborateur(
    data: CollaborateurCreate,
    # current_user: dict = Depends(verify_token)
):
    # if current_user["role"] not in ["GLOBAL_ADMIN", "RH_ADMIN"]:
    #     raise HTTPException(status_code=403, detail="Accès refusé")

    db = await get_db()
    tenant_id = "default"
    # current_user.get("tenant_id", "default")

    # Vérifier que le manager existe
    manager = await db.collaborateurs.find_one({
        "_id": ObjectId(data.managerId),
        "tenant_id": tenant_id
    })
    if not manager:
        raise HTTPException(status_code=400, detail="Manager non trouvé")

    # Vérifier unicité email + refFF
    if await db.collaborateurs.find_one({"email": data.email, "tenant_id": tenant_id}):
        raise HTTPException(status_code=400, detail="Email déjà utilisé")
    if await db.collaborateurs.find_one({"refFF": data.refFF, "tenant_id": tenant_id}):
        raise HTTPException(status_code=400, detail="REF FF déjà utilisé")

    collab = {
        **data.dict(),
        "tenant_id": tenant_id,
        "statut": "actif",
        "created_at": ObjectId().generation_time,
    }
    result = await db.collaborateurs.insert_one(collab)
    
    # MODIFICATION: Retourner l'objet complet pour Redux
    created_collab = await db.collaborateurs.find_one({"_id": result.inserted_id})
    created_collab["id"] = str(created_collab["_id"])
    del created_collab["_id"]
    
    return created_collab


# ──────────────────────────────────────
# LIRE UN COLLABORATEUR (GET /collaborateurs/{id})
# ──────────────────────────────────────
@router.get("/{collab_id}")
async def get_collaborateur(
    collab_id: str,
    # current_user: dict = Depends(verify_token)
):
    db = await get_db()
    collab = await get_collab_or_404(db, collab_id,"default")
                                    #   current_user.get("tenant_id", "default"))
    return collab


# ──────────────────────────────────────
# MODIFIER UN COLLABORATEUR (PUT /collaborateurs/{id})
# Retourne l'objet complet mis à jour
# ──────────────────────────────────────
@router.put("/{collab_id}")
async def update_collaborateur(
    collab_id: str,
    data: CollaborateurUpdate,
    # current_user: dict = Depends(verify_token)
):
    # if current_user["role"] not in ["GLOBAL_ADMIN", "RH_ADMIN"]:
    #     raise HTTPException(status_code=403, detail="Accès refusé")

    db = await get_db()
    # tenant_id = current_user.get("tenant_id", "default")
    tenant_id = "default"
    collab = await get_collab_or_404(db, collab_id, tenant_id)

    update_data = {k: v for k, v in data.dict().items() if v is not None}

    if "managerId" in update_data:
        manager = await db.collaborateurs.find_one({
            "_id": ObjectId(update_data["managerId"]), 
            "tenant_id": tenant_id
        })
        if not manager:
            raise HTTPException(status_code=400, detail="Nouveau manager invalide")

    if "email" in update_data and update_data["email"] != collab["email"]:
        if await db.collaborateurs.find_one({"email": update_data["email"], "tenant_id": tenant_id}):
            raise HTTPException(status_code=400, detail="Email déjà utilisé")

    if update_data:
        await db.collaborateurs.update_one(
            {"_id": ObjectId(collab_id)},
            {"$set": update_data}
        )
    
    # MODIFICATION: Retourner l'objet complet mis à jour pour Redux
    updated_collab = await db.collaborateurs.find_one({"_id": ObjectId(collab_id)})
    updated_collab["id"] = str(updated_collab["_id"])
    del updated_collab["_id"]
    
    return updated_collab


# ──────────────────────────────────────
# ARCHIVER / DÉSARCHIVER
# ──────────────────────────────────────
@router.patch("/{collab_id}/toggle-archive")
async def toggle_archive(
    collab_id: str,
    # current_user: dict = Depends(verify_token)
):
    # if current_user["role"] not in ["GLOBAL_ADMIN", "RH_ADMIN"]:
    #     raise HTTPException(status_code=403, detail="Accès refusé")

    db = await get_db()
    collab = await get_collab_or_404(db, collab_id,"default")
                                    #   current_user.get("tenant_id", "default"))

    new_status = "archive" if collab["statut"] == "actif" else "actif"
    await db.collaborateurs.update_one(
        {"_id": ObjectId(collab_id)},
        {"$set": {"statut": new_status}}
    )
    return {"statut": new_status}


# ──────────────────────────────────────
# SUPPRIMER (DELETE /collaborateurs/{id})
# Retourne l'ID supprimé pour Redux
# ──────────────────────────────────────
@router.delete("/{collab_id}")
async def delete_collaborateur(
    collab_id: str,
    # current_user: dict = Depends(verify_token)
):
    # if current_user["role"] not in ["GLOBAL_ADMIN", "RH_ADMIN"]:
    #     raise HTTPException(status_code=403, detail="Accès refusé")

    db = await get_db()
    tenant_id = "default"
    # tenant_id = current_user.get("tenant_id", "default")
    collab = await get_collab_or_404(db, collab_id, tenant_id)

    # Empêcher suppression si manager d'équipe
    has_team = await db.collaborateurs.count_documents({
        "managerId": collab_id,
        "tenant_id": tenant_id
    })
    if has_team > 0:
        raise HTTPException(
            status_code=400,
            detail="Impossible : ce manager a des collaborateurs. Archivez-les d'abord."
        )

    await db.collaborateurs.delete_one({"_id": ObjectId(collab_id)})
    
    # MODIFICATION: Retourner l'ID pour Redux (au lieu d'un message)
    return {"id": collab_id, "message": "Collaborateur supprimé définitivement"}