from fastapi import APIRouter, Depends, HTTPException
from app.schemas.campagne import CampagneCreate, CampagneOut
from app.core.security import verify_token
from app.db.mongodb import get_db
from app.models.evaluation import Evaluation
from typing import List

router = APIRouter()

@router.post("/campagnes/", response_model=CampagneOut)
async def create_campagne(campagne: CampagneCreate, current_user: dict = Depends(verify_token)):
    if current_user["role"] not in ["GLOBAL_ADMIN", "RH_ADMIN"]:
        raise HTTPException(status_code=403)
    db = await get_db()
    campagne_dict = campagne.dict()
    campagne_dict["tenant_id"] = current_user.get("tenant_id", "default")
    campagne_dict["statut"] = "brouillon"
    result = await db.campagnes.insert_one(campagne_dict)
    campagne_dict["id"] = str(result.inserted_id)

    # Génération auto des évaluations (comme dans l'exemple)
    collaborateurs = await db.collaborateurs.find({
        "fiche_fonction_id": {"$in": campagne.fiches_incluses},
        "tenant_id": campagne_dict["tenant_id"]
    }).to_list(1000)
    evaluations = []
    niveau_map = {"N1": 1, "N2": 2, "N3": 3, "N4": 4}
    for collab in collaborateurs:
        fiche = await db.fiches_fonction.find_one({"_id": collab["fiche_fonction_id"]})
        details = []
        for ref_comp in fiche.get("competences", []):
            comp = await db.competences.find_one({"ref_comp": ref_comp})
            if comp:
                details.append({
                    "ref_comp": ref_comp,
                    "niveau_attendu": comp["niveau_attendu"],
                    "niveau_observe": None,
                    "ecart": None,
                    "commentaire": ""
                })
        evals = {
            "campagne_id": campagne_dict["id"],
            "collaborateur_id": str(collab["_id"]),
            "manager_id": collab.get("manager_id"),
            "details": details,
            "statut": "en_attente",
            "tenant_id": campagne_dict["tenant_id"]
        }
        evaluations.append(evals)
    if evaluations:
        await db.evaluations.insert_many(evaluations)
        await db.campagnes.update_one({"_id": result.inserted_id}, {"$set": {"statut": "en_cours"}})
    return campagne_dict

@router.get("/campagnes/", response_model=List[CampagneOut])
async def list_campagnes(current_user: dict = Depends(verify_token)):
    db = await get_db()
    campagnes = await db.campagnes.find({"tenant_id": current_user.get("tenant_id", "default")}).to_list(length=1000)
    for c in campagnes:
        c["id"] = str(c["_id"])
        del c["_id"]
    return campagnes