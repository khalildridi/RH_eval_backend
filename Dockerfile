FROM python:3.9-slim

WORKDIR /app

# --- 1. Installer les dépendances système ---
RUN apt-get update && apt-get install -y \
    build-essential \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# --- 2. Copier et installer les dépendances Python ---
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- 3. Copier le code de l’application ---
COPY . .

# --- 4. Exposer le port ---
EXPOSE 8000

# --- 5. Créer le script de démarrage ---
# Ce script attend que Mongo soit prêt, initialise la DB, puis lance l’API
RUN echo '#!/bin/bash\n\
set -e\n\
echo "⏳ Attente de MongoDB..."\n\
until nc -z mongo 27017; do\n\
  sleep 2\n\
done\n\
echo "✅ MongoDB est prêt."\n\
python -m initialize_db.initialize_db || true\n\
echo "🚀 Lancement de l’API FastAPI..."\n\
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload' > /app/start.sh && \
chmod +x /app/start.sh

# --- 6. Lancer le script de démarrage ---
CMD ["/app/start.sh"]
