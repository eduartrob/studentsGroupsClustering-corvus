FROM python:3.11-slim

# Evitar que Python escriba archivos .pyc y forzar salida de logs sin búfer
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Directorio de trabajo en el contenedor
WORKDIR /app

# Instalar herramientas básicas necesarias (como curl para pruebas de conexión/healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias primero (para optimizar la caché de capas de Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código del proyecto
COPY . .

# Exponer el puerto en el que correrá FastAPI
EXPOSE 8000

# Comando para iniciar el microservicio
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
