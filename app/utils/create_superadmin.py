import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext

async def wait_for_mongo(uri):
    for i in range(10):
        try:
            client = AsyncIOMotorClient(uri)
            await client.admin.command('ping')
            print("✅ MongoDB prêt.")
            return client
        except Exception as e:
            print("⏳ En attente de MongoDB...")
            await asyncio.sleep(3)
    raise RuntimeError("MongoDB non disponible après 30s.")

async def create_superadmin():
    uri = "mongodb://mongo:27017"
    client = await wait_for_mongo(uri)
    db = client["rh_eval"]

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed = pwd_context.hash("terroubi")

    user = {
        "email": "superadmin@terroubi.com",
        "nom": "Super",
        "prenom": "Admin",
        "password_hash": hashed,
        "role": "GLOBAL_ADMIN",
        "tenant_id": "terroubi",
        "statut": "actif"
    }

    if await db.users.find_one({"email": user["email"]}) is None:
        result = await db.users.insert_one(user)
        print(f"✅ Super Admin créé avec ID: {result.inserted_id}")
    else:
        print("⚠️ Déjà existant !")

asyncio.run(create_superadmin())
