from fastapi import APIRouter, Depends, HTTPException
from app.models.evaluation import Evaluation, DetailEvaluation
from app.core.security import verify_token
from app.db.mongodb import get_db
from typing import List

router = APIRouter()

@router.get("/evaluations/", response_model=List[Evaluation])
async def list_evaluations(campagne_id: str = None, current_user: dict = Depends(verify_token)):
    db = await get_db()
    query = {"tenant_id": current_user.get("tenant_id", "default")}
    if campagne_id:
        query["campagne_id"] = campagne_id
    evaluations = await db.evaluations.find(query).to_list(length=1000)
    for e in evaluations:
        e["id"] = str(e["_id"])
        del e["_id"]
        # Calcul auto des écarts
        for detail in e["details"]:
            if detail["niveau_observe"]:
                niveau_map = {"N1": 1, "N2": 2, "N3": 3, "N4": 4}
                detail["ecart"] = niveau_map[detail["niveau_observe"]] - niveau_map[detail["niveau_attendu"]]
    return evaluations

@router.put("/evaluations/{eval_id}")
async def update_evaluation(eval_id: str, evaluation: Evaluation, current_user: dict = Depends(verify_token)):
    # Vérif manager ou RH
    if current_user["role"] not in ["GLOBAL_ADMIN", "RH_ADMIN", "MANAGER"]:
        raise HTTPException(status_code=403)
    db = await get_db()
    # Recalcul écarts
    niveau_map = {"N1": 1, "N2": 2, "N3": 3, "N4": 4}
    for detail in evaluation.details:
        if detail.niveau_observe:
            detail.ecart = niveau_map[detail.niveau_observe] - niveau_map[detail.niveau_attendu]
    await db.evaluations.update_one({"_id": eval_id}, {"$set": evaluation.dict(exclude={"id"})})
    return {"message": "Évaluation mise à jour"}