from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.core.security import verify_token
from app.db.mongodb import get_db
from typing import Dict, Any, List, Optional
from bson import ObjectId
from pydantic import BaseModel
import re

router = APIRouter(prefix="/managers", tags=["managers"])


# ──────────────────────────────────────
# MODELS
# ──────────────────────────────────────
class ManagerCreate(BaseModel):
    civilite: str
    prenom: str
    nom: str
    fonction: str
    refFF: str
    managerId: Optional[str] = None  # Un manager peut avoir un manager (hiérarchie)
    direction: str
    departement: str
    email: str
    isManager: bool


class ManagerUpdate(BaseModel):
    civilite: Optional[str] = None
    prenom: Optional[str] = None
    nom: Optional[str] = None
    fonction: Optional[str] = None
    refFF: Optional[str] = None
    managerId: Optional[str] = None
    direction: Optional[str] = None
    departement: Optional[str] = None
    email: Optional[str] = None
    statut: Optional[str] = None
    isManager: Optional[bool] = None


# ──────────────────────────────────────
# UTILS
# ──────────────────────────────────────
async def get_manager_or_404(db, manager_id: str, tenant_id: str):
    manager = await db.collaborateurs.find_one({
        "_id": ObjectId(manager_id),
        "tenant_id": tenant_id,
        # Optionnel: filtrer uniquement les managers
        # "fonction": {"$regex": "manager", "$options": "i"}
    })
    if not manager:
        raise HTTPException(status_code=404, detail="Manager non trouvé")
    manager["id"] = str(manager["_id"])
    del manager["_id"]
    return manager


def clean_search_term(term: str) -> str:
    return re.escape(term.strip().lower())


# ──────────────────────────────────────
# LISTE DES MANAGERS (GET /managers)
# ──────────────────────────────────────
@router.get("/", response_model=List[Dict[str, Any]])
async def list_managers(
    search: Optional[str] = Query(None, description="Recherche par nom, email"),
    statut: Optional[str] = Query(None, description="Filtre: actif | archive"),
    # current_user: dict = Depends(verify_token)
):
    db = await get_db()
    tenant_id ="default"
    # current_user.get("tenant_id", "default")
    
    # Query pour récupérer tous les collaborateurs qui sont managers
    # (ceux qui ont au moins un collaborateur sous eux)
    pipeline = [
        {"$match": {"tenant_id": tenant_id}},
        {
            "$lookup": {
                "from": "collaborateurs",
                "localField": "_id",
                "foreignField": "managerId",
                "as": "team"
            }
        },
        {"$match": {"team.0": {"$exists": True}}}  # A au moins 1 membre d'équipe
    ]
    
    # Alternative simple: récupérer tous les collaborateurs et filtrer côté application
    # Ou marquer explicitement les managers avec un champ "isManager"
    
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
        ]

    # Pour simplifier, on récupère tous les collaborateurs qui ont le mot "manager" dans leur fonction
    # OU qui ont des collaborateurs sous eux
    managers_cursor = db.collaborateurs.aggregate([
        {"$match": query},
        {
            "$lookup": {
                "from": "collaborateurs",
                "let": {"managerId": {"$toString": "$_id"}},
                "pipeline": [
                    {"$match": {"$expr": {"$eq": ["$managerId", "$$managerId"]}}}
                ],
                "as": "team"
            }
        },
        {
            "$match": {
                "$or": [
                    {"fonction": {"$regex": "manager", "$options": "i"}},
                    {"team.0": {"$exists": True}}
                ]
            }
        }
    ])
    
    managers = await managers_cursor.to_list(1000)
    for m in managers:
        m["id"] = str(m["_id"])
        del m["_id"]
        # Optionnel: ajouter le nombre de collaborateurs
        m["teamSize"] = len(m.get("team", []))
        if "team" in m:
            del m["team"]
    
    return managers


# ──────────────────────────────────────
# CRÉER UN MANAGER (POST /managers)
# ──────────────────────────────────────
@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_manager(
    data: ManagerCreate,
    # current_user: dict = Depends(verify_token)
):
    # if current_user["role"] not in ["GLOBAL_ADMIN", "RH_ADMIN"]:
    #     raise HTTPException(status_code=403, detail="Accès refusé")

    db = await get_db()
    # tenant_id = current_user.get("tenant_id", "default")
    tenant_id ="default"
    # Vérifier que le manager supérieur existe (si spécifié)
    if data.managerId:
        parent_manager = await db.collaborateurs.find_one({
            "_id": ObjectId(data.managerId),
            "tenant_id": tenant_id
        })
        if not parent_manager:
            raise HTTPException(status_code=400, detail="Manager supérieur non trouvé")

    # Vérifier unicité email + refFF
    if await db.collaborateurs.find_one({"email": data.email, "tenant_id": tenant_id}):
        raise HTTPException(status_code=400, detail="Email déjà utilisé")
    if await db.collaborateurs.find_one({"refFF": data.refFF, "tenant_id": tenant_id}):
        raise HTTPException(status_code=400, detail="REF FF déjà utilisé")

    manager = {
        **data.dict(),
        "tenant_id": tenant_id,
        "statut": "actif",
        "created_at": ObjectId().generation_time,
    }
    result = await db.collaborateurs.insert_one(manager)
    
    # Retourner l'objet complet
    created_manager = await db.collaborateurs.find_one({"_id": result.inserted_id})
    created_manager["id"] = str(created_manager["_id"])
    del created_manager["_id"]
    
    return created_manager


# ──────────────────────────────────────
# LIRE UN MANAGER (GET /managers/{id})
# ──────────────────────────────────────
@router.get("/{manager_id}")
async def get_manager(
    manager_id: str,
    # current_user: dict = Depends(verify_token)
):
    db = await get_db()
    manager = await get_manager_or_404(db, manager_id,"default")
                                        # current_user.get("tenant_id", "default"))
    tenant_id ="default"
    # Ajouter les informations d'équipe
    team = await db.collaborateurs.find({
        "managerId": manager_id,
        "tenant_id": tenant_id
        # current_user.get("tenant_id", "default")
    }).to_list(100)
    
    manager["team"] = [
        {
            "id": str(m["_id"]),
            "nom": m["nom"],
            "prenom": m["prenom"],
            "fonction": m["fonction"]
        } for m in team
    ]
    
    return manager


# ──────────────────────────────────────
# MODIFIER UN MANAGER (PUT /managers/{id})
# ──────────────────────────────────────
@router.put("/{manager_id}")
async def update_manager(
    manager_id: str,
    data: ManagerUpdate,
    # current_user: dict = Depends(verify_token)
):
    # if current_user["role"] not in ["GLOBAL_ADMIN", "RH_ADMIN"]:
    #     raise HTTPException(status_code=403, detail="Accès refusé")

    db = await get_db()
    tenant_id = "default"
    # current_user.get("tenant_id", "default")
    manager = await get_manager_or_404(db, manager_id, tenant_id)

    update_data = {k: v for k, v in data.dict().items() if v is not None}

    if "managerId" in update_data and update_data["managerId"]:
        parent_manager = await db.collaborateurs.find_one({
            "_id": ObjectId(update_data["managerId"]),
            "tenant_id": tenant_id
        })
        if not parent_manager:
            raise HTTPException(status_code=400, detail="Manager supérieur invalide")

    if "email" in update_data and update_data["email"] != manager["email"]:
        if await db.collaborateurs.find_one({"email": update_data["email"], "tenant_id": tenant_id}):
            raise HTTPException(status_code=400, detail="Email déjà utilisé")

    if update_data:
        await db.collaborateurs.update_one(
            {"_id": ObjectId(manager_id)},
            {"$set": update_data}
        )
    
    # Retourner l'objet mis à jour
    updated_manager = await db.collaborateurs.find_one({"_id": ObjectId(manager_id)})
    updated_manager["id"] = str(updated_manager["_id"])
    del updated_manager["_id"]
    
    return updated_manager


# ──────────────────────────────────────
# SUPPRIMER UN MANAGER (DELETE /managers/{id})
# ──────────────────────────────────────
@router.delete("/{manager_id}")
async def delete_manager(
    manager_id: str,
    # current_user: dict = Depends(verify_token)
):
    # if current_user["role"] not in ["GLOBAL_ADMIN", "RH_ADMIN"]:
    #     raise HTTPException(status_code=403, detail="Accès refusé")

    db = await get_db()
    tenant_id= "default"
    # tenant_id = current_user.get("tenant_id", "default")
    manager = await get_manager_or_404(db, manager_id, tenant_id)

    # Vérifier si le manager a une équipe
    team_count = await db.collaborateurs.count_documents({
        "managerId": manager_id,
        "tenant_id": tenant_id
    })
    
    if team_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Impossible : ce manager a {team_count} collaborateur(s). Réassignez-les d'abord."
        )

    await db.collaborateurs.delete_one({"_id": ObjectId(manager_id)})
    
    # Retourner l'ID pour Redux
    return {"id": manager_id, "message": "Manager supprimé définitivement"}


# ──────────────────────────────────────
# OBTENIR L'ÉQUIPE D'UN MANAGER
# ──────────────────────────────────────
@router.get("/{manager_id}/team")
async def get_manager_team(
    manager_id: str,
    # current_user: dict = Depends(verify_token)
):
    db = await get_db()
    tenant_id = "default"
    # tenant_id = current_user.get("tenant_id", "default")
    
    # Vérifier que le manager existe
    await get_manager_or_404(db, manager_id, tenant_id)
    
    # Récupérer son équipe
    team = await db.collaborateurs.find({
        "managerId": manager_id,
        "tenant_id": tenant_id,
        "statut": "actif"
    }).to_list(1000)
    
    for member in team:
        member["id"] = str(member["_id"])
        del member["_id"]
    
    return team