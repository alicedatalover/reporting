FROM python:3.11-slim

WORKDIR /app

# Copier le code source
COPY . .

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Commande par défaut 
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]