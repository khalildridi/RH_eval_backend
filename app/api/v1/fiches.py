from fastapi import APIRouter, Depends, HTTPException
from app.core.security import verify_token
from app.db.mongodb import get_db
from typing import List, Dict, Any

router = APIRouter()

@router.post("/fiches/")
async def create_fiche(fiche_data: Dict[str, Any], current_user: dict = Depends(verify_token)):
    if current_user["role"] not in ["GLOBAL_ADMIN", "RH_ADMIN"]:
        raise HTTPException(status_code=403)
    db = await get_db()
    fiche_data["tenant_id"] = current_user.get("tenant_id", "default")
    # Validation basique : compétences existent-elles ?
    for ref_comp in fiche_data.get("competences", []):
        comp = await db.competences.find_one({"ref_comp": ref_comp, "tenant_id": fiche_data["tenant_id"]})
        if not comp:
            raise HTTPException(status_code=400, detail=f"Compétence {ref_comp} introuvable")
    result = await db.fiches_fonction.insert_one(fiche_data)
    fiche_data["id"] = str(result.inserted_id)
    return fiche_data

@router.get("/fiches/", response_model=List[Dict[str, Any]])
async def list_fiches(current_user: dict = Depends(verify_token)):
    db = await get_db()
    fiches = await db.fiches_fonction.find({"tenant_id": current_user.get("tenant_id", "default")}).to_list(length=1000)
    for f in fiches:
        f["id"] = str(f["_id"])
        del f["_id"]
    return fiches