from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from app.api.v1 import auth, users, referentiels, fiches, collaborateurs, campagnes, evaluations,managers
from app.db.mongodb import connect_db, close_db

app = FastAPI(title="RH Eval Platform", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(referentiels.router, prefix="/api/v1")
app.include_router(fiches.router, prefix="/api/v1")
app.include_router(collaborateurs.router, prefix="/api/v1")
app.include_router(campagnes.router, prefix="/api/v1")
app.include_router(evaluations.router, prefix="/api/v1")
app.include_router(managers.router,prefix="/api/v1")

@app.on_event("startup")
async def startup_db_client():
    await connect_db()

@app.on_event("shutdown")
async def shutdown_db_client():
    await close_db()

@app.get("/")
async def root():
    return {"message": "RH Eval Platform Backend - Prêt !"}