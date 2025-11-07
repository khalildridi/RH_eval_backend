import pandas as pd
import io
from app.db.mongodb import get_db
from typing import Dict, Any

async def import_referentiel_csv(file_path: str, tenant_id: str) -> Dict[str, Any]:
    df = pd.read_csv(file_path)
    db = await get_db()

    # Créer référentiel si pas existant
    nom_ref = df["famille_metier"].iloc[0] if "famille_metier" in df.columns else "Référentiel par défaut"
    ref = await db.referentiels.find_one({"nom": nom_ref, "tenant_id": tenant_id})
    if not ref:
        ref_id = (await db.referentiels.insert_one({"nom": nom_ref, "type": "commun", "tenant_id": tenant_id})).inserted_id
    else:
        ref_id = ref["_id"]

    competences = []
    for _, row in df.iterrows():
        niveaux = {
            "N1": str(row.get("N1", "")),
            "N2": str(row.get("N2", "")),
            "N3": str(row.get("N3", "")),
            "N4": str(row.get("N4", ""))
        }
        comp = {
            "ref_comp": str(row["ref_comp"]),
            "ref_ff": str(row.get("ref_ff", "")),
            "domaine": str(row.get("domaine", "")),
            "axe": str(row.get("axe", "")),
            "categorie": str(row.get("categorie", "")),
            "definition": str(row.get("definition", "")),
            "niveaux": niveaux,
            "niveau_attendu": row.get("niveau_attendu", "N2"),
            "referentiel_id": ref_id,
            "tenant_id": tenant_id
        }
        competences.append(comp)
    
    # Upsert pour éviter doublons
    for comp in competences:
        await db.competences.replace_one(
            {"ref_comp": comp["ref_comp"], "tenant_id": tenant_id},
            comp,
            upsert=True
        )
    
    return {"referentiel_id": str(ref_id), "imported": len(competences)}

async def import_collaborateurs_csv(file_path: str, tenant_id: str) -> Dict[str, Any]:
    df = pd.read_csv(file_path)
    db = await get_db()
    collabs = []
    for _, row in df.iterrows():
        collab = {
            "user_id": str(row.get("user_id", "")),
            "matricule": str(row.get("matricule", "")),
            "poste": str(row.get("poste", "")),
            "departement": str(row.get("departement", "")),
            "manager_id": str(row.get("manager_id", "")),
            "fiche_fonction_id": str(row.get("fiche_fonction_id", "")),
            "date_embauche": row.get("date_embauche"),
            "statut": row.get("statut", "actif"),
            "tenant_id": tenant_id
        }
        collabs.append(collab)
    if collabs:
        await db.collaborateurs.insert_many(collabs, ordered=False)  # Ignore doublons
    return {"imported": len(collabs)}