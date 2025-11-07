from fastapi import APIRouter, Depends, HTTPException
from app.schemas.user import UserCreate, UserOut
from app.core.security import get_password_hash, verify_token
from app.db.mongodb import get_db
from app.models.user import User
from typing import List

router = APIRouter()

@router.post("/users/", response_model=UserOut)
async def create_user(user: UserCreate, current_user: dict = Depends(verify_token)):
    if current_user["role"] not in ["GLOBAL_ADMIN", "RH_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    db = await get_db()
    existing = await db.users.find_one({"email": user.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(user.password)
    user_dict = user.dict()
    user_dict["password_hash"] = hashed_password
    user_dict.pop("password")
    result = await db.users.insert_one(user_dict)
    user_dict["id"] = str(result.inserted_id)
    return user_dict

@router.get("/users/", response_model=List[UserOut])
async def read_users(skip: int = 0, limit: int = 100, current_user: dict = Depends(verify_token)):
    if current_user["role"] not in ["GLOBAL_ADMIN", "RH_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    db = await get_db()
    users = await db.users.find({"tenant_id": current_user.get("tenant_id", "default")}).skip(skip).limit(limit).to_list(length=limit)
    for u in users:
        u["id"] = str(u["_id"])
        del u["_id"]
        del u["password_hash"]
    return users